import sys
import yaml

from flask import Flask

from cms.site import Site

REQUIRED_OPTIONS = ["content_dir"]
# Optional options specified as (key, default value)
OPTIONAL_OPTIONS = [("default_page_config", {}), ("host", "localhost"),
                    ("port", 5000), ("template_dir", None),
                    ("static_dir", None), ("wsgi_socket", None)]

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

            # Make template and static directories default to the same place as
            # content
            if opt == "template_dir" or opt == "static_dir":
                config[opt] = config["content_dir"]

            else:
                config[opt] = default

    # Set static_url_path to something that will not be used, since Site will
    # deal with serving static files, since we need to serve from multiple
    # locations
    app = Flask(__name__, static_url_path="/flask_static")

    # Add default template and static dirs to config
    config["template_dirs"] = [config["template_dir"], "default_templates"]
    config["static_dirs"] = [config["static_dir"], "default_static"]

    site = Site(config, app)

    if config["wsgi_socket"] is None:
        app.run(debug=True, host=config["host"], port=config["port"])

    else:
        # Import the WSGI stuff here so that the user does not have to install
        # flup just to use flask server on local machine
        from flup.server.fcgi import WSGIServer
        print("Creating socket at {}".format(config["wsgi_socket"]))
        WSGIServer(app, bindAddress=config["wsgi_socket"]).run()
