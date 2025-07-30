

# Summary

Simple GUI for the <a href="">opencanary project</a>.

---


<div align="center">
  <img src="https://github.com/chrisjbawden/opencanary-ui/blob/main/misc/35345346.png" alt="O-UI Interface" style="width:70%; margin:auto;" />
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
  -e man_port=8001 \
  --cap-add NET_ADMIN \
  --restart unless-stopped \
  --cap-add NET_RAW \
  -e TZ=[your time zone] \
  chrisjbawden/opencanary-ui

```

