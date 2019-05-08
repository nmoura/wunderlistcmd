# wunderlistcmd
Tool to manipulate Wunderlist lists and tasks from the command line

## Usage
1. pypi3 install wunderpy2
2. create a file called `$HOME/.wunderlistcmd` with the following content:

```
[general]
access_token = <YOUR ACCESS TOKEN>
client_id = <YOUR CLIENT_ID>
```

In order to get your `access_token` and `client_id`, you should create an app
at https://developer.wunderlist.com/apps. You can put anything in APP URL and
AUTH CALLBACK URL fields.
