from django.urls import path
from .views import grade_handwritten_answer, grade_full_page_answers

urlpatterns = [
    path('grade/', grade_handwritten_answer, name='grade-answer'),
    path('grade-full-page/', grade_full_page_answers, name='grade-full-page' ),
]
