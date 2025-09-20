

<div align="center" > <p> # Opencanary Project </p></div>

Simple GUI for the <a href="https://github.com/thinkst/opencanary" target="_blank">opencanary project</a>.

---


<div align="center">
  <img src="https://github.com/chrisjbawden/opencanary-ui/blob/main/misc/35345346.png" alt="O-UI Interface" style="width:70%; margin:auto;" />
</div>


<hr>

## Access

1. If you, provided a port for the management console via environment variables (MA_PORT=?)
   <br>
   1.1 Open a browser, target the host IP and the port you set in step 1.
3. Open a browser, target the host IP with the default port 8501
4. Log in using the default credentials -
   <br>
      U: admin
   <br>
      P: admin
<br>
<br>
Note: to change the password, go settings > change password.

---

## Deployment

Docker run:
```
docker run -d \
  -v [directory on host]/opencanaryd:/etc/opencanaryd/ \
  -v [directory on host]/app:/app \
  --network host \
  --name opencanary \
  -e MA_PORT=8001 \
  --cap-add NET_ADMIN \
  --restart unless-stopped \
  --cap-add NET_RAW \
  -e TZ=[your time zone] \
  chrisjbawden/opencanary-ui

```

---

## Disclaimer:
This project is currently in active development and considered beta software. Features and functionality may change, and bugs or unexpected behaviour may occur. Use at your own risk. No guarantee is provided regarding stability, security, or fitness for any particular purpose.
