

# Summary

Simple GUI for the <a href="">opencanary project</a>.


<div align="center">
  <img src="https://github.com/chrisjbawden/cockpit-dockermanager/blob/main/misc/45634534573.png" alt="DockerManager Interface" style="width:70%; margin:auto;" />
</div>


<hr>

## Deployment

Docker run:
```
docker run -d \
  -v [directory on host]/opencanaryd:/etc/opencanaryd/ \
  -v [directory on host]/app:/app \
  --network host \
  --name opencanary \
  --cap-add NET_ADMIN \
  --restart unless-stopped \
  --cap-add NET_RAW \
  -e TZ=[your time zone] \
  chrisjbawden/opencanary-ui

```

