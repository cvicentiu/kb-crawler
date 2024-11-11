from django.db import models


class Page(models.Model):
    url = models.URLField(null=False, blank=False)
    title = models.CharField(max_length=400, null=False, blank=False)
    text = models.TextField(null=False, blank=False)


class PageEmbedding(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    embedding = models.BinaryField(null=False)
