import os

from . import data


REMOTE_REFS_BASE = 'refs/heads/'
LOCAL_REFS_BASE = 'refs/remote/'

def fetch(remote_path):
    # Get refs from server
    print('Will fetch the following refs:')
    refs = _get_remote_refs(remote_path, REMOTE_REFS_BASE)

    # Update loacal refs to match server
    for remote_name, value in refs.items():
        refname = os.path.relpatch(remote_name, REMOTE_BEFS_BASE)
        data.update_ref(f'{LOCAL_REFS_BASE}/{refname}',
                        data.RefValue(symbolic=False, value=value))


def _get_remote_refs(remote_path, prefix=''):
    with data.change_git_dir(remote_path):
        return {refname: ref.value for refname, ref in data.iter_refs(prefix)}
