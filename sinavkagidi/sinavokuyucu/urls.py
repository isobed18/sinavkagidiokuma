from django.urls import path
from .views import grade_handwritten_answer

urlpatterns = [
    path('grade/', grade_handwritten_answer, name='grade-answer'),
]
