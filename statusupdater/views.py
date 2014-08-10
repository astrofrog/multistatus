import requests

from django.shortcuts import redirect
from django.http import HttpResponse
from django.conf import settings

from urllib.parse import urlencode

from .models import User

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

    # TODO - should check state

    # Get access token

    base = "https://github.com/login/oauth/access_token"

    parameters = {}
    parameters['client_id'] = settings.GITHUB_CLIENT_ID
    parameters['client_secret'] = settings.GITHUB_CLIENT_SECRET
    parameters['code'] = code
    parameters['redirect_uri'] = "http://astrofrog.pythonanywhere.com/login-success"

    response = requests.post(base,
                             parameters,
                             headers={'Accept':'application/json'}).json()

    access_token = response['access_token']

    # Find current user

    parameters = {}
    parameters['access_token'] = access_token

    base = "https://api.github.com/user"

    response = requests.get(base, headers={'Authorization':'token ' + access_token}).json()

    login = response['login']

    # Create user in database

    user = User(username=login, access_token=access_token)
    user.save()

    return HttpResponse('Success! Now add a web hook to your GitHub repository')

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
    response = requests.post(base, parameters,
                             headers={'Authorization':'token ' + user.access_token})

    return HttpResponse('')
