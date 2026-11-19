from django.urls import path

from . import views

# This file is included at "login/" by the project urls.py.
urlpatterns = [
    path('', views.login_user),                                   # /login/  -> sign-in page
    path('login_user', views.login_user, name='login'),           # /login/login_user (kept: settings LOGIN_URL='login')
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout_user, name='logout'),            # POST only
    path('home/', views.home, name='home'),                       # old address -> new dashboard
]
