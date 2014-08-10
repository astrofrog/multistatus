from django.shortcuts import render, redirect, render_to_response
from django.http import HttpResponse
from django.conf import settings

from urllib.parse import urljoin, urlencode
from urllib.request import  urlopen, Request

from .models import User

import logging

# Create your views here.

def login(request):

    base = "https://github.com/login/oauth/authorize"

    parameters = {}
    parameters['client_id'] = settings.GITHUB_CLIENT_ID
    parameters['redirect_uri'] = "http://astrofrog.pythonanywhere.com/get_code"
    parameters['scope'] = 'repo:status'
    parameters['state'] = '1290jdjwoqj'

    url = base + '?' + urlencode(parameters)

    return redirect(url)

def get_code(request):
    
    code = request.GET.get('code')
    state = request.GET.get('state')
    
    # Get access token

    base = "https://github.com/login/oauth/access_token"

    parameters = {}
    parameters['client_id'] = settings.GITHUB_CLIENT_ID
    parameters['client_secret'] = settings.GITHUB_CLIENT_SECRET
    parameters['code'] = code
    parameters['redirect_uri'] = "http://astrofrog.pythonanywhere.com/login-success"

    url = Request(base, headers={'Accept':'application/json'})

    u = urlopen(url, urlencode(parameters).encode('ascii'))
    
    response = u.read()

    #return HttpResponse(response)

    import json
    response = json.loads(response.decode('utf-8'))

    access_token = response['access_token']

    parameters = {}
    parameters['access_token'] = access_token

    base = "https://api.github.com/user"

    url = Request(base, headers={'Authorization':'token ' + access_token})

    u = urlopen(url)

    response = u.read()

    response = json.loads(response.decode('utf-8'))

    login = response['login']

    User.objects.create(username=login, access_token=access_token)

    return HttpResponse('Success - now add a web hook')

def hook(response):

    if not 'HTTP_X_GITHUB_EVENT' in response.META:
        return HttpResponse('')

    if response.META['HTTP_X_GITHUB_EVENT'] != 'status':
        return HttpResponse('')

    import json
    response = json.loads(response.body.decode('utf-8'))

    if response.get('context') == 'statusupdater':
        return HttpResponse("won't comment on my own updates")

    sha = response.get('sha')
    state = response.get('state')

    name = response.get('name')

    owner, repo = name.split('/')

    base = 'https://api.github.com/repos/{owner}/{repo}/statuses/{sha}'.format(owner=owner, repo=repo, sha=sha)

    # TODO - won't work for organizations, or repo with multiple committers
    user = User.objects.get(username=owner)
    
    parameters = {}
    parameters['state'] = 'success'
    parameters['target_url'] = 'http://astrofrog.pythonanywhere.com'
    parameters['description'] = "This is a test of the multistatus webapp"
    parameters['context'] = 'statusupdater'

    parameters = json.dumps(parameters)

    import requests
    response = requests.post(base, parameters, headers={'Authorization':'token ' + user.access_token})

    return HttpResponse('')

