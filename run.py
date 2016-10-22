import sys
import yaml

from flask import Flask

from cms.site import Site

class Cms(object):

    REQUIRED_OPTIONS = ["content_dir"]
    # Optional options specified as (key, default value)
    OPTIONAL_OPTIONS = [("default_page_config", {}), ("host", "localhost"),
                        ("port", 5000), ("template_dirs", []),
                        ("static_dirs", []),
                        ("static_filetypes", ["js", "css", "png", "jpg", "gif",
                                              "html"])]

    def __init__(self, config_file):
        self.config = self.load_config(config_file)

        # Set static_url_path to something that will not be used, since Site will
        # deal with serving static files, since we need to serve from multiple
        # locations
        self.app = Flask(__name__, static_url_path="/flask_static")

        # Add content_dir to template_dirs and static_dirs
        self.config["template_dirs"].append(self.config["content_dir"])
        self.config["static_dirs"].append(self.config["content_dir"])

        self.site = Site(self.config, self.app)

    def load_config(self, filename):
        """Load a cms config file from the filename provided, check all required
        options and set default values. Return the config as a dictionary"""
        try:
            with open(filename) as f:
                config = yaml.load(f) or {}

        except IOError:
            print("cms: No such file {}".format(filename))
            sys.exit(1)

        # Check required options are present
        for opt in Cms.REQUIRED_OPTIONS:
            if opt not in config:
                print("cms: Invalid config: '{}' missing".format(opt))
                sys.exit(1)

        # Set default values for optional options are are not present
        for opt, default in Cms.OPTIONAL_OPTIONS:
            if opt not in config:
                config[opt] = default

        return config

    def run(self):
        """Run the flask app"""
        self.app.run(debug=True, host=self.config["host"],
                     port=self.config["port"])


if __name__ == "__main__":
    cms = Cms(sys.argv[1])

    if "export_to" in cms.config:
        cms.site.export_static(cms.config["export_to"])
        cms.site.export(cms.config["export_to"])
    else:
        cms.run()
