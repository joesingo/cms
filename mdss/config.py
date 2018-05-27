from collections import namedtuple


ConfigOption = namedtuple("ConfigOption", ["name", "default"])


class SiteConfig(dict):
    """
    Class to represent a global site configuration
    """
    options = [
        ConfigOption("templates_path", ["templates"]),
        ConfigOption("default_template", "base.html"),
    ]
    error_if_extra = True

    def __init__(self, d=None, **kwargs):
        """
        Initialise this config from another dictionary and validate items
        """
        super().__init__()

        d = d or {}
        if kwargs:
            d.update(kwargs)

        for opt in self.options:
            if opt.name in d:
                self[opt.name] = d.pop(opt.name)
            elif opt.default is not None:
                self[opt.name] = opt.default
            else:
                raise ValueError(
                    "Required value '{}' missing".format(opt.name)
                )

        if not self.error_if_extra:
            self.update(d)
        elif d:
            raise ValueError(
                "Unrecognised options: {}".format(", ".join(d.keys()))
            )

    def __getattr__(self, x):
        return self[x]
