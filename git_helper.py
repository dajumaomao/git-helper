import argparse
import logging
import subprocess

from git import Repo, InvalidGitRepositoryError, GitCommandError


def tag_prd(task):
    """
    分支打prd
    """
    tagged_branch = "BRANCH_" + task
    if not found_origin_branch('origin/' + tagged_branch):
        raise ValueError("task号没有远程分支:{}".format(tagged_branch))
    # checkout 要打tag 的分支
    checkout_branch(tagged_branch)
    # 确认与远端同步
    work_repo.remote().pull()
    # 获取最新的tag
    latest_prd = 'master' if get_latest_prd_tag() is None else get_latest_prd_tag()
    # 将最新的tag 合并到当前分支
    merge_code(tagged_branch, latest_prd)
    # push 合并之后的任务分支
    work_repo.remote().push()
    # checkout master分支
    # todo 会丢commit
    work_repo.git.stash()
    checkout_branch('master')
    work_repo.git.stash('pop')
    # 把任务分支合并到master分支上
    merge_code('master', tagged_branch)
    prd_tag = "PRD_" + task
    # 检查master 上是否已经有tag, 在master分支上面打tag
    tag_branch(prd_tag, 'master')
    # 推送tag
    push_tag(prd_tag)


def push_tag(tag):
    """
    推送tag
    """
    work_repo.git.push('origin', tag)


def tag_branch(tag, branch):
    """
    给branch 打tag
    """
    check_current_branch(branch)
    if tag in work_repo.tags:
        raise ValueError("tag:{}已存在".format(tag))
    work_repo.create_tag(tag)


def merge_code(branch, ref):
    """
    合并
    """
    check_current_branch(branch)
    try:
        work_repo.index.merge_tree(ref)
    except GitCommandError:
        confirm = input("合并遇到冲突,请手动解决后输入 continue 回车继续")
        if confirm == 'continue':
            merge_code(branch, ref)


def get_latest_prd_tag():
    """
    获取最新的PRD tag
    """
    tags = work_repo.tags
    if len(tags) > 0:
        return str(sorted(tags, key=lambda t: t.commit.committed_datetime)[-1])
    return None


def create_origin_branch(branch):
    """
    基于master创建远程分支
    """
    if args.verbose:
        logging.info("创建远程分支 {}".format(branch))
    work_repo.git.push('origin', branch)


def create_local_branch(branch):
    """
    创建本地分支
    """
    if args.verbose:
        logging.info("创建本地分支 {}".format(branch))
    work_repo.create_head(branch)


def found_local_branch(branch):
    """
    查找本地的分支
    """
    return branch in get_all_local_branches(work_repo)


def found_origin_branch(branch):
    """
    查找远程的分支
    """
    return branch in get_all_remote_branches(work_repo)


def checkout_branch(branch):
    """
    切换到分支
    """
    work_repo.git.checkout(branch)


def get_branch_name(branch):
    return branch.name


def get_all_local_branches(repo):
    """
    获取本地分支
    """
    return list(map(get_branch_name, repo.branches))


def get_all_remote_branches(repo):
    """
    获取远端分支
    """
    return list(map(get_branch_name, repo.remotes.origin.refs))


def check_current_branch(branch):
    """
    检查当前分支是否正确
    """
    current_branch = work_repo.active_branch
    if current_branch.name != branch:
        raise ValueError("当前分支不正确 branch:{}".format(branch))


def make_diff(task):
    """
    arc diff
    """
    check_current_branch(task)
    origin_branch = "BRANCH_" + task
    if found_origin_branch(origin_branch):
        subprocess.run(['arc', 'diff', '--create', origin_branch], check=True)
    else:
        raise ValueError("没有找到要diff的远程分支:{},task:{}".format(origin_branch, task))


def land_diff(task):
    """
    向哪个分支land 不允许land to master
    """
    origin_branch = 'BRANCH_' + task
    check_current_branch(task)
    if not found_origin_branch(origin_branch):
        raise ValueError("没有找到要land的远程分支:{},task:{}".format(origin_branch, task))
    subprocess.run(['arc', 'land', '--onto', origin_branch], check=True)


def init_task(task):
    """
    创建一个新任务的工作分支 和 基于master创建远程分支
    """
    origin_branch = "BRANCH_" + task
    if not found_origin_branch(origin_branch):
        create_origin_branch('master:' + origin_branch)
    if not found_local_branch(task):
        create_local_branch(task)
    checkout_branch(task)


def check_task_id_format(task):
    """
    检查task号的格式
    """
    if not task.startswith("T"):
        raise ValueError("task号必须T开头")
    return True


def handle_args():
    """解析脚本参数"""
    method = args.method
    task = args.task
    check_task_id_format(task)
    if method == 'init':
        """初始化工作分支"""
        init_task(task)
    elif method == 'diff':
        """创建 arc diff"""
        make_diff(task)
    elif method == 'land':
        """land arc diff"""
        land_diff(task)
    elif method == 'prd':
        """打prd"""
        tag_prd(task)
    else:
        print("不支持的操作")


parser = argparse.ArgumentParser(description='Task处理工具')
parser.add_argument('method', action='store', type=str, choices=['init', 'diff', 'land', 'prd'], help='要执行的操作')
parser.add_argument('-v', '--verbose', help='打印详细信息', required=False, action='store_true')
parser.add_argument('-t', '--task', type=str, help='task号', required=True)
parser.add_argument('-p', '--path', type=str, help='task工作目录,默认为当前目录', default='.', required=False)

args = parser.parse_args()
try:
    work_repo = Repo(args.path)
except InvalidGitRepositoryError:
    raise ValueError("指定的目录不是Git仓库目录")
if __name__ == "__main__":
    handle_args()
