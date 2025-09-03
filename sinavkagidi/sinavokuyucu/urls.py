from django.urls import path
from .views import grade_handwritten_answer, grade_full_page_answers, grade_text_answer, grade_multiple_text_answers

urlpatterns = [
    path('grade/', grade_handwritten_answer, name='grade-answer'),
    path('grade-full-page/', grade_full_page_answers, name='grade-full-page'),
    path('grade-text/', grade_text_answer, name='grade-text'),
    path('grade-multiple-text/', grade_multiple_text_answers, name='grade-multiple-text'),
]