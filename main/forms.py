from django import forms

class ProjectForm(forms.Form):
    planet=forms.CharField(max_length=100)
    
    