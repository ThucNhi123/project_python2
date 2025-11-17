from django.db import models

class UserProfile(models.Model):
    session_key = models.CharField(max_length=40, unique=True)
    
    age = models.IntegerField()
    sex = models.CharField(max_length=10)
    height = models.FloatField()
    weight = models.FloatField()
    heart_rate = models.FloatField()
    body_temp = models.FloatField()
    efficiency = models.FloatField()
    intensity = models.IntegerField()

    def __str__(self):
        return f"Profile {self.session_key}"