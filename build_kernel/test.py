#!/usr/bin/python3

""" Tests build_kernel.py """

import unittest
import build_kernel


class TestBuildKernel(unittest.TestCase):

    def test_version_compare_major(self):
        old = build_kernel.VersionInfo(version_triple="4.7.10", vmlinuz="vmlinuz-4.7.10-gentoo",
                                       system_map="System.map-4.7.10-gentoo", config="config-4.7.10-gentoo", is_old=False)
        new = build_kernel.VersionInfo(version_triple="5.7.10", vmlinuz="vmlinuz-5.7.10-gentoo",
                                       system_map="System.map-5.7.10-gentoo", config="config-5.7.10-gentoo", is_old=False)
        # Greater is newer
        self.assertGreater(new, old)

    def test_version_compare_minor(self):
        old = build_kernel.VersionInfo(version_triple="5.6.10", vmlinuz="vmlinuz-5.6.10-gentoo",
                                       system_map="System.map-5.6.10-gentoo", config="config-5.6.10-gentoo", is_old=False)
        new = build_kernel.VersionInfo(version_triple="5.7.10", vmlinuz="vmlinuz-5.7.10-gentoo",
                                       system_map="System.map-5.7.10-gentoo", config="config-5.7.10-gentoo", is_old=False)
        # Greater is newer
        self.assertGreater(new, old)

    def test_version_compare_patch(self):
        old = build_kernel.VersionInfo(version_triple="5.7.9", vmlinuz="vmlinuz-5.7.9-gentoo",
                                       system_map="System.map-5.7.9-gentoo", config="config-5.7.9-gentoo", is_old=False)
        new = build_kernel.VersionInfo(version_triple="5.7.10", vmlinuz="vmlinuz-5.7.10-gentoo",
                                       system_map="System.map-5.7.10-gentoo", config="config-5.7.10-gentoo", is_old=False)
        # Greater is newer
        self.assertGreater(new, old)

    def test_version_compare_old(self):
        old = build_kernel.VersionInfo(version_triple="5.7.10", vmlinuz="vmlinuz-5.7.10-gentoo.old",
                                       system_map="System.map-5.7.10-gentoo.old", config="config-5.7.10-gentoo.old", is_old=True)
        new = build_kernel.VersionInfo(version_triple="5.7.10", vmlinuz="vmlinuz-5.7.10-gentoo",
                                       system_map="System.map-5.7.10-gentoo", config="config-5.7.10-gentoo", is_old=False)
        # Greater is newer
        self.assertGreater(new, old)


if __name__ == '__main__':
    unittest.main()
