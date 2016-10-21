import sys
import yaml

from flask import Flask

from cms.site import Site

REQUIRED_OPTIONS = ["content_dir"]
# Optional options specified as (key, default value)
OPTIONAL_OPTIONS = [("default_page_config", {}), ("host", "localhost"),
                    ("port", 5000), ("template_dirs", []),
                    ("static_dirs", []),
                    ("static_filetypes", ["js", "css", "png", "jpg", "gif",
                                          "html"])]

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

    # Set static_url_path to something that will not be used, since Site will
    # deal with serving static files, since we need to serve from multiple
    # locations
    app = Flask(__name__, static_url_path="/flask_static")

    # Add content_dir to template_dirs and static_dirs
    config["template_dirs"].append(config["content_dir"])
    config["static_dirs"].append(config["content_dir"])

    site = Site(config, app)

    if "export_to" in config:
        site.export_static(config["export_to"])
        site.export(config["export_to"])
    else:
        app.run(debug=True, host=config["host"], port=config["port"])
