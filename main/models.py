from django.db import models

# Create your models here.

class PlanetData(models.Model):
    body=models.CharField(max_length=100)
    date=models.TextField()
    utc=models.TextField()
    azim=models.FloatField(max_length=5)
    elev=models.FloatField()
    inM=models.FloatField()
    inKm=models.FloatField()
    rv=models.FloatField()
    ilumn=models.FloatField()
    rise=models.TextField()
    fall=models.TextField()
    zone=models.TextField()

    def body_image_url(self):
        return f"/static/main/{self.body.lower()}_image.jpeg"

