"""Metrics collection and export for playbook executions."""

import socket
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional


class MetricType(Enum):
    """Type of metric."""

    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"


@dataclass
class MetricValue:
    """Value for a metric with labels."""

    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """
    Collect and store metrics for playbook executions.

    Thread-safe metrics collection with support for counters,
    histograms, and gauges.

    Example:
        metrics = MetricsCollector()
        metrics.increment_counter("playbook_executions_total", {"playbook": "test", "status": "success"})
        metrics.observe_histogram("playbook_duration_seconds", 1.25, {"playbook": "test"})
        print(f"Total executions: {metrics.get_counter('playbook_executions_total')}")
    """

    def __init__(self, retention_seconds: int = 3600) -> None:
        """
        Initialize metrics collector.

        Args:
            retention_seconds: How long to retain metric values (default: 1 hour)
        """
        self.retention_seconds = retention_seconds
        self._lock = Lock()

        # Store metrics by type
        self._counters: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self._histograms: Dict[str, List[MetricValue]] = defaultdict(list)
        self._gauges: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        # Metadata about metrics
        self._metric_types: Dict[str, MetricType] = {}
        self._metric_help: Dict[str, str] = {}

    def increment_counter(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        value: float = 1.0,
        help_text: Optional[str] = None,
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: Metric name
            labels: Label key-value pairs
            value: Amount to increment (default: 1.0)
            help_text: Optional help text for the metric
        """
        labels = labels or {}
        label_key = self._make_label_key(labels)

        with self._lock:
            self._metric_types[name] = MetricType.COUNTER
            if help_text and name not in self._metric_help:
                self._metric_help[name] = help_text

            self._counters[name][label_key] += value

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        help_text: Optional[str] = None,
    ) -> None:
        """
        Record a histogram observation.

        Args:
            name: Metric name
            value: Observed value
            labels: Label key-value pairs
            help_text: Optional help text for the metric
        """
        labels = labels or {}

        with self._lock:
            self._metric_types[name] = MetricType.HISTOGRAM
            if help_text and name not in self._metric_help:
                self._metric_help[name] = help_text

            metric_value = MetricValue(value=value, labels=labels)
            self._histograms[name].append(metric_value)

            # Clean up old values
            self._cleanup_histogram(name)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        help_text: Optional[str] = None,
    ) -> None:
        """
        Set a gauge metric value.

        Args:
            name: Metric name
            value: Gauge value
            labels: Label key-value pairs
            help_text: Optional help text for the metric
        """
        labels = labels or {}
        label_key = self._make_label_key(labels)

        with self._lock:
            self._metric_types[name] = MetricType.GAUGE
            if help_text and name not in self._metric_help:
                self._metric_help[name] = help_text

            self._gauges[name][label_key] = value

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """
        Get counter value.

        Args:
            name: Metric name
            labels: Label key-value pairs (if None, returns sum of all labels)

        Returns:
            Counter value
        """
        with self._lock:
            if name not in self._counters:
                return 0.0

            if labels is None:
                # Return sum of all label combinations
                return sum(self._counters[name].values())

            label_key = self._make_label_key(labels)
            return self._counters[name].get(label_key, 0.0)

    def get_histogram_values(
        self, name: str, labels: Optional[Dict[str, str]] = None
    ) -> List[float]:
        """
        Get histogram values.

        Args:
            name: Metric name
            labels: Label key-value pairs (if None, returns all values)

        Returns:
            List of observed values
        """
        with self._lock:
            if name not in self._histograms:
                return []

            values = self._histograms[name]

            if labels is None:
                return [v.value for v in values]

            # Filter by labels
            return [
                v.value
                for v in values
                if all(v.labels.get(k) == val for k, val in labels.items())
            ]

    def get_histogram_stats(
        self, name: str, labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """
        Get histogram statistics.

        Args:
            name: Metric name
            labels: Label key-value pairs

        Returns:
            Dict with count, sum, min, max, avg, p50, p95, p99
        """
        values = self.get_histogram_values(name, labels)

        if not values:
            return {
                "count": 0,
                "sum": 0.0,
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "count": count,
            "sum": sum(sorted_values),
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "avg": sum(sorted_values) / count,
            "p50": self._percentile(sorted_values, 0.50),
            "p95": self._percentile(sorted_values, 0.95),
            "p99": self._percentile(sorted_values, 0.99),
        }

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """
        Get gauge value.

        Args:
            name: Metric name
            labels: Label key-value pairs

        Returns:
            Gauge value
        """
        with self._lock:
            if name not in self._gauges:
                return 0.0

            if labels is None:
                # Return last set value (arbitrary if multiple labels)
                values = list(self._gauges[name].values())
                return values[-1] if values else 0.0

            label_key = self._make_label_key(labels)
            return self._gauges[name].get(label_key, 0.0)

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics as a dictionary.

        Returns:
            Dict with all metric names, types, and values
        """
        with self._lock:
            result: Dict[str, Any] = {}

            for name, metric_type in self._metric_types.items():
                if metric_type == MetricType.COUNTER:
                    result[name] = {
                        "type": "counter",
                        "help": self._metric_help.get(name, ""),
                        "values": dict(self._counters[name]),
                    }
                elif metric_type == MetricType.HISTOGRAM:
                    result[name] = {
                        "type": "histogram",
                        "help": self._metric_help.get(name, ""),
                        "stats": self.get_histogram_stats(name),
                    }
                elif metric_type == MetricType.GAUGE:
                    result[name] = {
                        "type": "gauge",
                        "help": self._metric_help.get(name, ""),
                        "values": dict(self._gauges[name]),
                    }

            return result

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()
            self._metric_types.clear()
            self._metric_help.clear()

    def _make_label_key(self, labels: Dict[str, str]) -> str:
        """Create a unique key for label combination."""
        if not labels:
            return ""
        # Sort labels for consistent keys
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def _cleanup_histogram(self, name: str) -> None:
        """Remove old histogram values beyond retention period."""
        cutoff_time = time.time() - self.retention_seconds
        self._histograms[name] = [
            v for v in self._histograms[name] if v.timestamp >= cutoff_time
        ]

    def _percentile(self, sorted_values: List[float], p: float) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        k = (len(sorted_values) - 1) * p
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_values) else f

        if f == c:
            return sorted_values[f]

        # Linear interpolation
        return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


class PrometheusExporter:
    """Export metrics in Prometheus text format."""

    def __init__(self, metrics: MetricsCollector) -> None:
        """
        Initialize Prometheus exporter.

        Args:
            metrics: MetricsCollector instance
        """
        self.metrics = metrics

    def export(self) -> str:
        """
        Export metrics in Prometheus text format.

        Returns:
            Prometheus-formatted metrics text
        """
        lines: List[str] = []
        all_metrics = self.metrics.get_all_metrics()

        for name, metric_data in sorted(all_metrics.items()):
            metric_type = metric_data["type"]
            help_text = metric_data.get("help", "")

            # Add HELP and TYPE comments
            if help_text:
                lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} {metric_type}")

            if metric_type == "counter" or metric_type == "gauge":
                # Export counter/gauge values
                for label_str, value in sorted(metric_data["values"].items()):
                    if label_str:
                        labels_formatted = "{" + label_str.replace("=", '="') + '"}'
                        lines.append(f"{name}{labels_formatted} {value}")
                    else:
                        lines.append(f"{name} {value}")

            elif metric_type == "histogram":
                # Export histogram as buckets
                stats = metric_data["stats"]
                buckets = [
                    0.005,
                    0.01,
                    0.025,
                    0.05,
                    0.1,
                    0.25,
                    0.5,
                    1.0,
                    2.5,
                    5.0,
                    10.0,
                ]

                values = self.metrics.get_histogram_values(name)
                for le in buckets:
                    count = sum(1 for v in values if v <= le)
                    lines.append(f'{name}_bucket{{le="{le}"}} {count}')

                # Add +Inf bucket
                lines.append(f'{name}_bucket{{le="+Inf"}} {stats["count"]}')
                lines.append(f'{name}_sum {stats["sum"]}')
                lines.append(f'{name}_count {stats["count"]}')

            lines.append("")  # Blank line between metrics

        return "\n".join(lines)


class StatsDExporter:
    """Export metrics to StatsD."""

    def __init__(
        self,
        metrics: MetricsCollector,
        host: str = "localhost",
        port: int = 8125,
        prefix: str = "playbooks",
    ) -> None:
        """
        Initialize StatsD exporter.

        Args:
            metrics: MetricsCollector instance
            host: StatsD host
            port: StatsD port
            prefix: Metric name prefix
        """
        self.metrics = metrics
        self.host = host
        self.port = port
        self.prefix = prefix
        self._socket: Optional[socket.socket] = None

    def flush(self) -> None:
        """Send metrics to StatsD."""
        try:
            self._ensure_socket()
            all_metrics = self.metrics.get_all_metrics()

            for name, metric_data in all_metrics.items():
                metric_type = metric_data["type"]
                full_name = f"{self.prefix}.{name}"

                if metric_type == "counter":
                    for label_str, value in metric_data["values"].items():
                        metric_name = self._format_metric_name(full_name, label_str)
                        self._send(f"{metric_name}:{value}|c")

                elif metric_type == "gauge":
                    for label_str, value in metric_data["values"].items():
                        metric_name = self._format_metric_name(full_name, label_str)
                        self._send(f"{metric_name}:{value}|g")

                elif metric_type == "histogram":
                    stats = metric_data["stats"]
                    self._send(f"{full_name}.count:{stats['count']}|c")
                    self._send(f"{full_name}.avg:{stats['avg']:.6f}|g")
                    self._send(f"{full_name}.p95:{stats['p95']:.6f}|g")
                    self._send(f"{full_name}.p99:{stats['p99']:.6f}|g")

        except Exception:
            # Silently fail - don't crash execution due to metrics
            pass

    def close(self) -> None:
        """Close StatsD socket."""
        if self._socket:
            self._socket.close()
            self._socket = None

    def _ensure_socket(self) -> None:
        """Ensure socket is created."""
        if not self._socket:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _format_metric_name(self, name: str, label_str: str) -> str:
        """Format metric name with labels for StatsD."""
        if not label_str:
            return name

        # Convert labels to dot-separated format
        # e.g., "playbook=test,status=success" -> "playbook.test.status.success"
        label_parts = []
        for part in label_str.split(","):
            if "=" in part:
                key, val = part.split("=", 1)
                label_parts.extend([key, val])

        return f"{name}.{'.'.join(label_parts)}"

    def _send(self, message: str) -> None:
        """Send message to StatsD."""
        if self._socket:
            self._socket.sendto(message.encode(), (self.host, self.port))
