import json
import uuid
import requests

from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.conf import settings

from urllib.parse import urlencode

from .models import User

# Create your views here.

def login(request):

    base = "https://github.com/login/oauth/authorize"

    parameters = {}
    parameters['client_id'] = settings.GITHUB_CLIENT_ID
    parameters['redirect_uri'] = settings.SITE_URL + "/get_code"
    parameters['scope'] = 'repo:status'

    # TODO - state should be random
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
    parameters['redirect_uri'] = settings.SITE_URL + "/login-success"

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

    try:
        user = User.objects.get(username=login)
    except User.DoesNotExist:
        user = User(username=login, access_token=access_token, hook_id=str(uuid.uuid1()))

    user.login_count += 1
    user.save()

    # Create hook url
    hook_url = settings.SITE_URL + "/hook/{hook_id}/".format(hook_id=user.hook_id)

    # Return instructions on setting up webhook
    return render(request, 'statusupdater/success.html', {'hook_url': hook_url})

def hook(response, hook_id):

    # If call is not from GitHub, we should just ignore
    if not 'HTTP_X_GITHUB_EVENT' in response.META:
        return HttpResponse('')

    # We only listen to status updates
    if response.META['HTTP_X_GITHUB_EVENT'] != 'status':
        return HttpResponse('')

    response = json.loads(response.body.decode('utf-8'))

    # We avoid any circular triggering
    if response.get('context') == 'github-multi-status':
        return HttpResponse("won't comment on my own updates")

    # Get the SHA of the commit that triggered the change
    sha = response.get('sha')

    # Find repo name, split into owner and repository
    name = response.get('name')
    owner, repo = name.split('/')

    # Get the list of available statuses in reverse chronological order
    base = 'https://api.github.com/repos/{owner}/{repo}/commits/{sha}/statuses'.format(owner=owner, repo=repo, sha=sha)
    response = requests.get(base).json()

    # Loop over and keep track only of the latest status for a given context
    status_dict = {}
    descr_dict = {}
    for status in response:
        context = status['context']
        if context not in status_dict and context != 'default' and context != 'github-multi-status':
            status_dict[context] = status['state']
            descr_dict[context] = status['description']

    if len(status_dict) <= 1:
        return HttpResponse("Single status, nothing to do")

    # Figure out resulting state
    if 'pending' in status_dict.values():
        final_state = 'pending'
    elif 'error' in status_dict.values():
        final_state = 'error'
    elif 'failure' in status_dict.values():
        final_state = 'failure'
    else:
        final_state = 'success'

    # Figure out combined description
    final_description = ' / '.join(sorted(descr_dict.values()))

    # Update status on PR

    base = 'https://api.github.com/repos/{owner}/{repo}/statuses/{sha}'.format(owner=owner, repo=repo, sha=sha)

    user = User.objects.get(hook_id=hook_id)
    user.hook_count += 1
    user.save()

    parameters = {}
    parameters['state'] = final_state
    parameters['target_url'] = settings.SITE_URL + '/view?owner={owner}&repo={repo}&sha={sha}'.format(owner=owner, repo=repo, sha=sha)
    parameters['description'] = final_description
    parameters['context'] = 'github-multi-status'

    parameters = json.dumps(parameters)

    response = requests.post(base, parameters,
                             headers={'Authorization':'token ' + user.access_token})

    return HttpResponse("Using user=" + user.username + " and hook_id=" + hook_id + "\nResponse:\n\n" + response.content.decode('utf-8'))

def status_links(request):

    owner = request.GET.get('owner')
    repo = request.GET.get('repo')
    sha = request.GET.get('sha')

    # Get the list of available statuses in reverse chronological order
    base = 'https://api.github.com/repos/{owner}/{repo}/commits/{sha}/statuses'.format(owner=owner, repo=repo, sha=sha)
    response = requests.get(base).json()

    # Loop over and keep track only of the latest status for a given context
    unique_state = {}
    for status in response:
        context = status['context']
        if context not in unique_state and context != 'default' and context != 'github-multi-status':
            unique_state[context] = status

    return render(request, 'statusupdater/view.html', {'unique':unique_state})

def index(request):
    return render(request, 'statusupdater/index.html', {})
