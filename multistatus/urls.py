from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from statusupdater import views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'multistatus.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^login', views.login), 
    url(r'^get_code', views.get_code),
    url(r'^hook/(?<hook_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/', views.hook),
)
