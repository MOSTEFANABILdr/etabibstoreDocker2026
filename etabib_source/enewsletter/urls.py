from django.urls import path

from enewsletter import admin

urlpatterns = [
    path('message/preview/<int:pk>', admin.NewsLetterAdmin.previewMessage, name="newsletter-message-preview"),
    path('news-criteria-choices-autocomplete', admin.NewsCriteriaChoicesAutocomplete.as_view(), name="news-criteria-choices-autocomplete"),
]