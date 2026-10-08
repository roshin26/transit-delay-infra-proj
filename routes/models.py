from django.db import models

# Create your models here.
class Route(models.Model):
    route_id = models.CharField(max_length=50, primary_key=True)  
    short_name = models.CharField(max_length=10)                   
    long_name = models.CharField(max_length=255)                   
    mode = models.CharField(max_length=10, default="bus")

    def __str__(self):
        return self.short_name


class DelayReading(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='delay_readings')
    trip_id = models.CharField(max_length=100)
    stop_id = models.CharField(max_length=50)
    delay_seconds = models.IntegerField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['route', 'recorded_at']),
        ]

class FetchLog(models.Model):
    fetched_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField()
    record_count = models.IntegerField(default=0)
    error_message = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-fetched_at']