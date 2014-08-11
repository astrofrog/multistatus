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
    url(r'^hook/(?P<hook_id>[^/]+)/$', views.hook),
    url(r'^$', views.index),
    url(r'^view', views.status_links),

)
