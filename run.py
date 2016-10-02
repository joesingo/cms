import sys
import yaml

from flask import Flask

from cms.site import Site

if __name__ == "__main__":
    config_file = sys.argv[1]

    try:
        with open(config_file) as f:
            config = yaml.load(f) or {}

    except IOError:
        print("cms: No such file {}".format(config_file))
        sys.exit(1)

    try:
        app = Flask(__name__, template_folder=config["template_dir"],
                    static_folder=config["static_dir"])
        site = Site(config)

        app.route("/<path:url>/")(site.view_page)
        app.route("/", defaults={"url": ""})(site.view_page)

        app.run(debug=True, host=config["host"], port=config["port"])

    except KeyError as e:
        print("cms: Invalid config: '{}' missing".format(e.message.split()[-1]))

