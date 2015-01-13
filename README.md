Deployment 
==========

Development environment
-----------------------

### Prerequisites:

- [Virtualbox](https://www.virtualbox.org/)
- [Vagrant](https://www.vagrantup.com/)

### Step-by-step guide:

1. `git clone https://github.com/notapresent/rtrss.git`
2. `cd rtrss`
3. `vagrant up`
4. `vagrant ssh`
4. ... TODO


Production deployment on [Openshift](https://www.openshift.com/)
--------------------------------------------------------------------------------

### Prerequisites: 

- Openshift account. You can create one [here](https://www.openshift.com/app/account/new).
- OpenShift Client Tools ([installation instructions](https://developers.openshift.com/en/managing-client-tools.html)). Don't forget to run `rhc setup` before first use.
- Google developer console project. Create one [here](https://console.developers.google.com/project).
- Service account, associated with the project from previous step. [Here](https://developers.google.com/console/help/new/#serviceaccounts) you can find instructions how to create one. 
- Private key in JSON format. Find your service account in Credentials section, then click `[Generate new JSON key]`. You need to store this file somewhere, so it can be downloaded via public URL, services like [Dropbox](https://www.dropbox.com/) will do.
- Google Cloud Storage bucket. By default, each new project gets default bucket, named `<Project id>.appspot.com`

### Step-by-step guide:

1. Clone application code: `git clone https://github.com/notapresent/rtrss.git`
2. `cd rtrss`
3. Choose a name: `export APP_NAME='<your app name here>'`
4. Create openshift application: `rhc create-app --no-git --no-dns "$APP_NAME" python-2.7 postgresql-9.2`. Note `Git remote` url in command output. Add optional `--scaling` parameter to create scalable app.
5. Pull in created repo  `git pull --strategy=ours --no-edit <Git remote url from previous step>`
6. Set up configuration values: `rhc set-env --app $APP_NAME RTRSS_SECRET_KEY='<Secret key>' RTRSS_GCS_BUCKET_NAME='<Bucket name>' RTRSS_APIKEY_URL='<Private key URL>'`
7. Push the code: `git push <Git remote url> master`. Sometimes this fails with message `The remote end hung up unexpectedly`, In this case just run the command again :)
8. TODO...
