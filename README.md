Configuration
=============

Application settings: 

`RTRSS_SECRET_KEY` - secret key used by Flask to sign cookies. Set this to some random, hard to guess string.
`RTRSS_FILESTORAGE_URL` - URL for torrent file storage. Supported schemes are `gs://` and `file://`. 
* `file://` is used to store torrent files in local directory. With this scheme, you can use values of other environment variables like this: `file://{$ENVVAR_NAME}/torrents`.
* `gs://` scheme is used to store files in Google Cloud Storage: `gs://<Storage bucket id>/[prefix]`.  Prefix is optional.
    On Openshift default value is `file://{$OPENSHIFT_DATA_DIR}/torrents`, in local development environment it defaults to `file://<Project dir>/data/torrents`
`RTRSS_GCS_PRIVATEKEY_URL` - If you use Google Cloud Storage to store torrent files, this must be set to location of private key file in JSON format.

Settings are stored in environment variables, default value is used if variable not set.


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

1. Choose a name: `export APP_NAME='<Your app name here>'`
2. Create openshift application: `rhc create-app "$APP_NAME" python-2.7 postgresql-9.2`
3. `cd $APP_NAME`
4. `git remote add upstream -m master https://github.com/notapresent/rtrss.git`
5. `git pull -s recursive -X theirs --no-edit upstream master`
6. Set up configuration values: `rhc set-env RTRSS_SECRET_KEY='<Secret key>' RTRSS_FILESTORAGE_URL='<Storage URL>'`
7. Push code to openshift: `git push`
8. TODO