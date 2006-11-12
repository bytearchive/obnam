import ConfigParser
import os
import shutil
import tempfile
import unittest

import obnam


class LocalBackendBase(unittest.TestCase):

    def setUp(self):
        self.cachedir = "tmp.cachedir"
        self.rootdir = "tmp.rootdir"
        
        os.mkdir(self.cachedir)
        os.mkdir(self.rootdir)
        
        config_list = (
            ("backup", "cache-dir", self.cachedir),
            ("backup", "local-store", self.rootdir)
        )
    
        self.config = obnam.config.default_config()
        for section, item, value in config_list:
            if not self.config.has_section(section):
                self.config.add_section(section)
            self.config.set(section, item, value)

        self.cache = obnam.cache.init(self.config)

    def tearDown(self):
        shutil.rmtree(self.cachedir)
        shutil.rmtree(self.rootdir)
        del self.cachedir
        del self.rootdir
        del self.config


class InitTests(LocalBackendBase):

    def testInit(self):
        be = obnam.backend.init(self.config, self.cache)
        self.failUnlessEqual(be.local_root, self.rootdir)


class IdTests(LocalBackendBase):

    def testGenerateBlockId(self):
        be = obnam.backend.init(self.config, self.cache)
        self.failIfEqual(be.curdir, None)
        id = obnam.backend.generate_block_id(be)
        self.failUnless(id.startswith(be.curdir))
        id2 = obnam.backend.generate_block_id(be)
        self.failIfEqual(id, id2)


class UploadTests(LocalBackendBase):

    def testUpload(self):
        be = obnam.backend.init(self.config, self.cache)
        id = obnam.backend.generate_block_id(be)
        block = "pink is pretty"
        ret = obnam.backend.upload(be, id, block)
        self.failUnlessEqual(ret, None)
        
        pathname = os.path.join(self.rootdir, id)
        self.failUnless(os.path.isfile(pathname))
        
        f = file(pathname, "r")
        data = f.read()
        f.close()
        self.failUnlessEqual(block, data)


class DownloadTests(LocalBackendBase):

    def testOK(self):
        be = obnam.backend.init(self.config, self.cache)
        id = obnam.backend.generate_block_id(be)
        block = "pink is still pretty"
        obnam.backend.upload(be, id, block)
        
        success = obnam.backend.download(be, id)
        self.failUnlessEqual(success, None)
        
    def testError(self):
        be = obnam.backend.init(self.config, self.cache)
        id = obnam.backend.generate_block_id(be)
        success = obnam.backend.download(be, id)
        self.failIfEqual(success, True)


class FileListTests(LocalBackendBase):

    def testFileList(self):
        be = obnam.backend.init(self.config, self.cache)
        self.failUnlessEqual(obnam.backend.list(be), [])
        
        id = "pink"
        block = "pretty"
        obnam.backend.upload(be, id, block)
        list = obnam.backend.list(be)
        self.failUnlessEqual(list, [id])

        filename = os.path.join(self.rootdir, id)
        f = file(filename, "r")
        block2 = f.read()
        f.close()
        self.failUnlessEqual(block, block2)


class RemoveTests(LocalBackendBase):

    def test(self):
        be = obnam.backend.init(self.config, self.cache)
        id = obnam.backend.generate_block_id(be)
        block = "pink is still pretty"
        obnam.backend.upload(be, id, block)

        self.failUnlessEqual(obnam.backend.list(be), [id])
        
        obnam.backend.remove(be, id)
        self.failUnlessEqual(obnam.backend.list(be), [])