"""VCS tests: Bazaar."""

import os
import subprocess
from ..testing import COMMIT_USER_FULL
from ..testing import VcsTestCase
from ..bzr import BzrBranch
from ..bzr import working_directory_keeper
from ..base import UpdateError


class BzrBaseTestCase(VcsTestCase):
    """Common utilities for Bazaard test cases."""

    def create_src(self):
        os.chdir(self.src_dir)
        subprocess.call(['bzr', 'init', 'src-branch'])
        self.src_repo = os.path.join(self.src_dir, 'src-branch')
        os.chdir(self.src_repo)
        subprocess.call(['bzr', 'whoami', '--branch', COMMIT_USER_FULL])
        f = open('tracked', 'w')
        f.write("first" + os.linesep)
        f.close()
        subprocess.call(['bzr', 'add'])
        subprocess.call(['bzr', 'commit', '-m', 'initial commit'])
        f = open('tracked', 'w')
        f.write("last" + os.linesep)
        f.close()
        subprocess.call(['bzr', 'commit', '-m', 'last version'])

    def assertRevision(self, branch, rev, first_line):
        """Assert that branch is at prescribed revision

        Double check with expected first line of 'tracked' file."""
        target_dir = branch.target_dir
        self.assertTrue(os.path.isdir(target_dir))
        f = open(os.path.join(target_dir, 'tracked'))
        lines = f.readlines()
        f.close()
        self.assertEquals(lines[0].strip(), first_line)
        self.assertEquals(branch.parents(), [rev])

    def assertRevision1(self, branch):
        """Assert that branch is at revision 1."""
        self.assertRevision(branch, '1', 'first')

    def assertRevision2(self, branch):
        """Assert that branch is at revision 2."""
        self.assertRevision(branch, '2', 'last')


class BzrTestCase(BzrBaseTestCase):

    def test_branch(self):
        target_dir = os.path.join(self.dst_dir, "My branch")
        branch = BzrBranch(target_dir, self.src_repo)
        branch('last:1')
        self.assertRevision2(branch)

    def test_branch_stacked(self):
        target_dir = os.path.join(self.dst_dir, "My branch")
        branch = BzrBranch(target_dir, self.src_repo,
                           **{'bzr-stacked-branches': 'True'})
        branch('last:1')
        self.assertRevision2(branch)

    def test_branch_to_rev(self):
        """Directly clone and update to given revision."""
        target_dir = os.path.join(self.dst_dir, "My branch")
        branch = BzrBranch(target_dir, self.src_repo)
        branch('1')
        self.assertRevision1(branch)

    def test_update(self):
        """Update to a revision that's not the latest available in target"""
        target_dir = os.path.join(self.dst_dir, "clone to update")
        branch = BzrBranch(target_dir, self.src_repo)('last:1')

        # Testing starts here
        branch = BzrBranch(target_dir, self.src_repo)
        branch('1')
        self.assertRevision1(branch)

    def test_update_tag(self):
        """Update to an avalailable rev, identified by tag.
        """
        with working_directory_keeper:
            os.chdir(self.src_repo)
            subprocess.check_call(['bzr', 'tag', '-r', '1', 'sometag'])

        target_dir = os.path.join(self.dst_dir, "clone to update")

        # Testing starts here
        branch = BzrBranch(target_dir, self.src_repo)
        branch('sometag')
        self.assertRevision1(branch)

    def test_update_needs_pull(self):
        """Update to a revision that needs to be pulled from target."""
        target_dir = os.path.join(self.dst_dir, "clone to update")
        branch = BzrBranch(target_dir, self.src_repo)('1')

        # Testing starts here
        branch = BzrBranch(target_dir, self.src_repo)
        branch('2')
        self.assertRevision2(branch)

    def test_archive(self):
        target_dir = os.path.join(self.dst_dir, "clone to archive")
        branch = BzrBranch(target_dir, self.src_repo)
        branch('1')

        archive_dir = os.path.join(self.dst_dir, "archive directory")
        branch.archive(archive_dir)
        with open(os.path.join(archive_dir, 'tracked')) as f:
            self.assertEquals(f.readlines()[0].strip(), 'first')

    def test_url_update(self):
        """Method to update branch.conf does it and stores old values"""
        # Setting up a prior branch
        target_dir = os.path.join(self.dst_dir, "clone to update")
        branch = BzrBranch(target_dir, self.src_repo)
        branch('1')
        # src may have become relative, let's keep it in that form
        old_src = branch.parse_conf()['parent_location']

        # first rename.
        # We test that pull actually works rather than
        # just checking branch.conf to avoid logical loop testing nothing
        new_src = os.path.join(self.src_dir, 'new-src-repo')
        os.rename(self.src_repo, new_src)
        branch = BzrBranch(target_dir, new_src)
        branch('last:1')

        self.assertEquals(branch.parse_conf(), dict(
            buildout_save_parent_location_1=old_src,
            parent_location=new_src))

        # second rename
        new_src2 = os.path.join(self.src_dir, 'new-src-repo2')
        os.rename(new_src, new_src2)
        branch = BzrBranch(target_dir, new_src2)
        branch('1')

        self.assertEquals(branch.parse_conf(), dict(
            buildout_save_parent_location_1=old_src,
            buildout_save_parent_location_2=new_src,
            parent_location=new_src2))

    def test_url_update_1133248(self):
        """Method to update branch.conf is resilient wrt to actual content.

        See lp:1133248 for details
        """
        # Setting up a prior branch
        target_dir = os.path.join(self.dst_dir, "clone to update")
        branch = BzrBranch(target_dir, self.src_repo)
        branch('1')

        conf_path = os.path.join(target_dir, '.bzr', 'branch', 'branch.conf')
        with open(conf_path, 'a') as conf:
            conf.seek(0, os.SEEK_END)
            conf.write(os.linesep + "Some other stuff" + os.linesep)

        # src may have become relative, let's keep it in that form
        old_src = branch.parse_conf()['parent_location']

        # first rename.
        # We test that pull actually works rather than
        # just checking branch.conf to avoid logical loop testing nothing
        new_src = os.path.join(self.src_dir, 'new-src-repo')
        os.rename(self.src_repo, new_src)
        branch = BzrBranch(target_dir, new_src)
        branch('last:1')

        self.assertEquals(branch.parse_conf(), dict(
            buildout_save_parent_location_1=old_src,
            parent_location=new_src))

    def test_lp_url(self):
        """lp: locations are being rewritten to the actual target."""
        branch = BzrBranch('', 'lp:anybox.recipe.openerp')
        # just testing for now that it's been rewritten
        self.failIf(branch.url.startswith('lp:'))

        # checking idempotency of rewritting
        branch2 = BzrBranch('', branch.url)
        self.assertEquals(branch2.url, branch.url)

    def test_lp_url_nobzrlib(self):
        """We can't safely handle lp: locations without bzrlib."""
        from anybox.recipe.openerp import vcs
        save = vcs.bzr.LPDIR
        vcs.bzr.LPDIR = None
        self.assertRaises(RuntimeError, BzrBranch, '', 'lp:something')
        vcs.bzr.LPDIR = save

    def test_update_clear_locks(self):
        """Testing update with clear locks option."""
        # Setting up a prior branch
        target_dir = os.path.join(self.dst_dir, "clone to update")
        BzrBranch(target_dir, self.src_repo)('last:1')

        # Testing starts here
        branch = BzrBranch(target_dir, self.src_repo, clear_locks=True)
        branch('1')
        self.assertRevision1(branch)

    def test_failed(self):
        target_dir = os.path.join(self.dst_dir, "My branch")
        branch = BzrBranch(target_dir, '/does-not-exist')
        self.assertRaises(subprocess.CalledProcessError,
                          branch.get_update, 'default')


class BzrOfflineTestCase(BzrBaseTestCase):

    def make_local_branch(self, path, initial_rev):
        """Make a local branch of the source at initial_rev and forbid pulls.
        """
        target_dir = os.path.join(self.dst_dir, path)
        # initial branching (non offline
        BzrBranch(target_dir, self.src_repo)(initial_rev)

        # crippled offline branch
        branch = BzrBranch(target_dir, self.src_repo, offline=True)

        def _pull():
            raise UpdateError("Should not pull !")

        branch._pull = _pull
        return branch

    def test_update_needs_pull(self):
        """[offline mode] updating to a non available rev raises UpdateError.
        """
        branch = self.make_local_branch("clone to update", '1')
        self.assertRaises(UpdateError, branch, '2')

    def test_update_last(self):
        """[offline mode] update to a last:1 rev does nothing."""
        branch = self.make_local_branch("clone to update", '1')
        branch('last:1')
        self.assertRevision1(branch)

    def test_update_available_revno(self):
        """[offline mode] update to an available revno works"""
        branch = self.make_local_branch("clone to update", 'last:1')
        branch('1')
        self.assertRevision1(branch)

    def test_update_available_revid(self):
        """[offline mode] update to an available revid works.
        """
        branch = self.make_local_branch("clone to update", 'last:1')
        revid = branch.get_revid('1')
        branch('revid:' + revid)
        self.assertRevision1(branch)