import git
import logging

def get_repo(path_abs_repository):
    try:
        repo = git.Repo(path_abs_repository)
    except git.exc.InvalidGitRepositoryError:
        repo = init_repo(path_abs_repository)
    except Exception as e:
        raise e
    return repo


def init_repo(path_abs_repository):
    return git.Repo.init(path_abs_repository)


def set_config(repo, *config):
    repo.git.config(config)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    path = r"C:\Users\vince\Documents\GDriveGadz\PASS"
    repo = get_repo(path)
    repo.git.execute(["git", "add", "."])
    repo.git.execute(["git", "commit", "-m", "bla"])
    repo.git.execute(["git", "push"])
