from django.conf.urls import url
from django.urls import path

from econgre.views import organizer_views, speaker_views, moderateur_views, doctor_views

urlpatterns = [
    url(r'^organizer/dashboard/$', organizer_views.dashboard, name='organizer-dashboard'),

    # Congress urls
    url(r'^organizer/congress/my', organizer_views.CongressDatatableView.as_view(), name='organizer-congress-my'),
    url(r'^organizer/congress/create', organizer_views.CreateCongressView.as_view(), name='organizer-congress-create'),
    url(r'^organizer/congress/update/(?P<pk>\d+)', organizer_views.UpdateCongressView.as_view(),
        name='organizer-congress-update'),
    url(r'^organizer/congress/cancel/(?P<pk>\d+)', organizer_views.CancelCongressView.as_view(),
        name='organizer-congress-cancel'),
    url(r'^organizer/congress/publish/(?P<pk>\d+)', organizer_views.PublishCongressView.as_view(),
        name='organizer-congress-publish'),
    url(r'^organizer/congress/archive/(?P<pk>\d+)', organizer_views.ArchiveCongressView.as_view(),
        name='organizer-congress-archive'),
    path('organizer/congress/<int:pk>', organizer_views.CongressDetailView.as_view(),
         name='organizer-congress-detail'),

    #Webinar Urls
    url(r'^organizer/webinar/create/(?P<congre_pk>\d+)', organizer_views.CreateWebinarView.as_view(),
        name='organizer-webinar-create'),
    url(r'^organizer/webinar/update/(?P<pk>\d+)/(?P<congre_pk>\d+)', organizer_views.UpdateWebiarView.as_view(), name='organizer-webinar-update'),
    url(r'^organizer/webinar/publish/(?P<pk>\d+)', organizer_views.PublishWebiarView.as_view(), name='organizer-webinar-publish'),
    url(r'^organizer/webinar/publishall/(?P<congre_pk>\d+)', organizer_views.PublishAllWebiars, name='organizer-webinar-publish-all'),
    url(r'^organizer/webinar/archive/(?P<pk>\d+)', organizer_views.ArchiveWebiarView.as_view(), name='organizer-webinar-archive'),
    path('organizer/webinar/<int:pk>', organizer_views.WebinarDetailView.as_view(), name='organizer-webinar-detail'),
    url(r'^organizer/webinar/participants/(?P<webinar_pk>\d+)', organizer_views.ParticipantDatatableView.as_view(),
        name='organizer-webinar-medecinsparticipants'),

    #Webinar video
    url(r'^organizer/webinar/video/create/(?P<webinar_pk>\d+)$', organizer_views.WebinarVideoَCreateView.as_view(),
        name='organizer-webinar-video-create'),
    url(r'^organizer/webinar/video/cancel/(?P<pk>\d+)$', organizer_views.WebinarVideoCancelView.as_view(),
        name='organizer-webinar-video-cancel'),

    #Webinar Link
    url(r'^organizer/webinar/url/create/(?P<webinar_pk>\d+)$', organizer_views.WebinarUrlCreateView.as_view(),
        name='organizer-webinar-url-create'),
    url(r'^organizer/webinar/url/cancel/(?P<pk>\d+)$', organizer_views.WebinarUrlCancelView.as_view(),
        name='organizer-webinar-url-cancel'),

    # Invitation Urls
    url(r'^organizer/congress/invitations/(?P<pk>\d+)', organizer_views.InvitationDatatableView.as_view(),
        name='organizer-congress-invitations'),
    url(r'^organizer/congress/invitations/send/(?P<congre_pk>\d+)/(?P<type>\d+)', organizer_views.SendInvitationsView.as_view(),
        name='organizer-congress-invitations-send'),
    url(r'^accept-invite/(?P<key>\w+)/?$', organizer_views.AcceptInvitation.as_view(),
        name='accept-invite'),
    # Speacker Urls
    url(r'^organizer/speaker/add/(?P<webinar_pk>\d+)', organizer_views.CreateSpeakerView.as_view(),
        name='organizer-speaker-add'),
    url(r'^organizer/speaker/remove/(?P<pk>\d+)/(?P<speaker_pk>\d+)', organizer_views.CancelSpeakerView.as_view(),
        name='organizer-speaker-remove'),
    # Moderateur Urls
    url(r'^organizer/moderateur/add/(?P<webinar_pk>\d+)', organizer_views.CreateModerateurView.as_view(),
        name='organizer-moderateur-add'),
    url(r'^organizer/moderateur/remove/(?P<pk>\d+)/(?P<moderateur_pk>\d+)', organizer_views.CancelModerateurView.as_view(),
        name='organizer-moderateur-remove'),
    url(r'^organizer/profile/$', organizer_views.profile, name='organizer-profile'),

    # Profile speaker Urls
    url(r'^speaker/dashboard/$', speaker_views.dashboard, name='speaker-dashboard'),
    url(r'^speaker/profile/$', speaker_views.profile, name='speaker-profile'),
    url(r'^speaker/webinar/list$', speaker_views.WebinarDatatableView.as_view(), name='speaker-webinar-list'),
    path('speaker/webinar/<int:pk>', organizer_views.WebinarDetailView.as_view(),
         name='speaker-webinar-detail'),

    # Profile moderator Urls
    url(r'^moderator/dashboard/$', moderateur_views.dashboard, name='moderator-dashboard'),
    url(r'^moderator/webinar/list$', moderateur_views.WebinarDatatableView.as_view(), name='moderator-webinar-list'),
    path('moderator/webinar/<int:pk>', organizer_views.WebinarDetailView.as_view(),
         name='moderator-webinar-detail'),

    # Autocomplte
    url(r'^speaker-autocomplete', organizer_views.SpeakerAutocomplete.as_view(), name='speaker-autocomplete'),
    url(r'^moderateur-autocomplete', organizer_views.ModerateurAutocomplete.as_view(), name='moderateur-autocomplete'),

    # Uploads
    url(r'^sponsor-image-upload/$', organizer_views.sponsorImageUpload, name='sponsor-image-upload'),
    url(r'^congre-image-upload/$', organizer_views.congreImageUpload, name='congre-image-upload'),

    #doctor urls
    path('doctor/congress/list', doctor_views.congressList, name='doctor-congress-list'),
    url('doctor/congress/participate/$', doctor_views.participateWebinar, name='doctor-participate-congre'),
    url('doctor/congress/detail/(?P<pk>\d+)/$', organizer_views.CongressDetailView.as_view(),
        name='doctor-congress-detail'),
    path('doctor/webinar/join/<int:pk>', organizer_views.WebinarDetailView.as_view(),
         name='doctor-webinar-join'),

]
