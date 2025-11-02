from django.db import models

# Create your models here.
class Survey(models.Model):
    age = models.IntegerField()
    gender = models.CharField(max_length=20)
    height = models.FloatField()
    weight = models.FloatField()
    bpm = models.IntegerField()
    temperature = models.FloatField()
    efficiency = models.FloatField()
    intensity = models.IntegerField()

    def __str__(self):
        return f"Survey of {self.gender} - {self.age} tuổi"