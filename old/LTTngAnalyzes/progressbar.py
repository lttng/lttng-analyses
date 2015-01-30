import os
import sys

try:
    from progressbar import ETA, Bar, Percentage, ProgressBar
    progressbar_available = True
except ImportError:
    progressbar_available = False

# approximation for the progress bar
BYTES_PER_EVENT = 30


def getFolderSize(folder):
    total_size = os.path.getsize(folder)
    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            total_size += os.path.getsize(itempath)
        elif os.path.isdir(itempath):
            total_size += getFolderSize(itempath)
    return total_size


def progressbar_setup(obj, args):
    if hasattr(args, "no_progress") and args.no_progress:
        obj.pbar = None
        return

    if progressbar_available:
        size = getFolderSize(args.path)
        widgets = ['Processing the trace: ', Percentage(), ' ',
                   Bar(marker='#', left='[', right=']'),
                   ' ', ETA(), ' ']  # see docs for other options
        obj.pbar = ProgressBar(widgets=widgets,
                               maxval=size/BYTES_PER_EVENT)
        obj.pbar.start()
    else:
        print("Warning: progressbar module not available, "
              "using --no-progress.", file=sys.stderr)
        args.no_progress = True
        obj.pbar = None
    obj.event_count = 0


def progressbar_update(obj, args):
    if hasattr(args, "no_progress") and \
            (args.no_progress or obj.pbar is None):
        return
    try:
        obj.pbar.update(obj.event_count)
    except ValueError:
        pass
    obj.event_count += 1


def progressbar_finish(obj, args):
    if hasattr(args, "no_progress") and args.no_progress:
        return
    obj.pbar.finish()
