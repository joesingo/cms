import sys
import yaml

from flask import Flask

from cms.site import Site

REQUIRED_OPTIONS = ["template_dir", "content_dir", "static_dir"]
# Optional options specified as (key, default value)
OPTIONAL_OPTIONS = [("default_page_config", {}), ("host", "localhost"),
                    ("port", 5000)]

if __name__ == "__main__":
    config_file = sys.argv[1]

    try:
        with open(config_file) as f:
            config = yaml.load(f) or {}

    except IOError:
        print("cms: No such file {}".format(config_file))
        sys.exit(1)

    # Check required options are present
    for opt in REQUIRED_OPTIONS:
        if opt not in config:
            print("cms: Invalid config: '{}' missing".format(opt))
            sys.exit(1)

    # Set default values for optional options are are not present
    for opt, default in OPTIONAL_OPTIONS:
        if opt not in config:
            config[opt] = default

    app = Flask(__name__, template_folder=config["template_dir"],
                static_folder=config["static_dir"])

    site = Site(config)

    app.route("/<path:url>/")(site.view_page)
    app.route("/", defaults={"url": ""})(site.view_page)

    app.run(debug=True, host=config["host"], port=config["port"])
