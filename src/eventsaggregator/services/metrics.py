from prometheus_client import Counter, Gauge, Histogram

# HTTP metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# EventsAPI metrics
events_provider_requests_total = Counter(
    "events_provider_requests_total",
    "Count requests to EventsAPI",
    ["endpoint", "status"],
)
events_provider_request_duration_seconds = Histogram(
    "events_provider_request_duration_seconds",
    "EventsAPI request duration",
    ["endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# Cache metrics
cache_hits_total = Counter(
    "cache_hits_total",
    "Total hits cache",
)
cache_misses_total = Counter(
    "cache_misses_total",
    "Total misses cache",
)

# Business metrics
tickets_created_total = Gauge("tickets_created_total", "Total created ticket")
events_total = Gauge("events_total", "Total events")
