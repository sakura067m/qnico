import sys
if __package__:
    from . import NicoDownloader
else:
    from importlib import import_module
    from pathlib import Path
    path = Path(sys.modules[__name__].__file__)
    sys.path.insert(0, str(path.parents[1]))
    package = import_module(path.parts[-2])
    NicoDownloader = package.NicoDownloader

def main():
    if len(sys.argv)>1:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("videoid", help="input the video id")
        parser.add_argument("-g",
                            "--getname",
                            help="get name from title",
                            action="store_true"
                            )  # default: False
        parser.add_argument("-s",
                            "--savehere",
                            help="save here immediate",
                            action="store_false"
                            )  # default: True
        args = parser.parse_args()
        print(args.videoid,args.getname,args.savehere)
        NicoDownloader.go(args.videoid, args.getname, args.savehere)
    else:
        NicoDownloader.openwindow()

if __name__ == "__main__":
    main()