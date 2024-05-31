# titiler-stacapi-mspc

<p align="center">
  <img width="800" src="https://github.com/developmentseed/titiler-stacapi/assets/10407788/bb54162e-9a47-4a67-99e5-6dc91098e048">
  <p align="center">Connect titiler to MS Planetary Computer STAC API</p>
</p>

<p align="center">
  <a href="https://github.com/developmentseed/titiler-stacapi-mspc/actions?query=workflow%3ACI" target="_blank">
      <img src="https://github.com/developmentseed/titiler-stacapi-mspc/workflows/CI/badge.svg" alt="Test">
  </a>
  <a href="https://codecov.io/gh/developmentseed/titiler-stacapi-mspc" target="_blank">
      <img src="https://codecov.io/gh/developmentseed/titiler-stacapi-mspc/branch/main/graph/badge.svg" alt="Coverage">
  </a>
  <a href="https://github.com/developmentseed/titiler-stacapi-mspc/blob/main/LICENSE" target="_blank">
      <img src="https://img.shields.io/github/license/developmentseed/titiler-stacapi-mspc.svg" alt="License">
  </a>
</p>

---

**Documentation**: <a href="https://developmentseed.org/titiler-stacapi-mspc/" target="_blank">https://developmentseed.org/titiler-stacapi-mspc/</a>

**Source Code**: <a href="https://github.com/developmentseed/titiler-stacapi-mspc" target="_blank">https://github.com/developmentseed/titiler-stacapi-mspc</a>

---

## Installation

Install from sources and run for development:

```
$ git clone https://github.com/developmentseed/titiler-stacapi-mspc.git
$ cd titiler-stacapi-mspc
$ virtualenv -p python3 venv
$ source venv/bin/activate
$ python -m pip install -e .
```

## Launch

By default the `stac_api_url` is https://planetarycomputer.microsoft.com/api/stac/v1, but you can override it by setting the environment variable `TITILER_STACAPI_STAC_API_URL`.

```
python -m pip install uvicorn

uvicorn titiler.stacapi.main:app --port 8000
```

### Using Docker

```
$ git clone https://github.com/developmentseed/titiler-stacapi-mspc.git
$ cd titiler-stacapi-mspc
$ docker-compose up --build api
```

It runs `titiler.stacapi` using Gunicorn web server.

### How it works

![](https://github.com/developmentseed/titiler-stacapi/assets/10407788/2e53bfe3-402a-4c57-bf61-c055e32f1362)

## Contribution & Development

See [CONTRIBUTING.md](https://github.com//developmentseed/titiler-stacapi-mspc/blob/main/CONTRIBUTING.md)

## License

See [LICENSE](https://github.com//developmentseed/titiler-stacapi-mspc/blob/main/LICENSE)

## Authors

See [contributors](https://github.com/developmentseed/titiler-stacapi-mspc/graphs/contributors) for a listing of individual contributors.

## Changes

See [CHANGELOG.md](https://github.com/developmentseed/titiler-stacapi-mspc/blob/main/CHANGELOG.md).
