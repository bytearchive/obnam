import os
import shutil
import tempfile
import unittest


import obnam


class ResolveTests(unittest.TestCase):

    def test(self):
        context = obnam.context.create()
        # We don't need the fields that are usually initialized manually.

        facit = (
            (".", "/", "/"),
            (".", "/pink", "/pink"),
            (".", "pink", "./pink"),
            ("pink", "/", "/"),
            ("pink", "/pretty", "/pretty"),
            ("pink", "pretty", "pink/pretty"),
            ("/pink", "/", "/"),
            ("/pink", "/pretty", "/pretty"),
            ("/pink", "pretty", "/pink/pretty"),
            ("/", "/", "/"),
        )

        for target, pathname, resolved in facit:
            context.config.set("backup", "target-dir", target)
            x = obnam.io.resolve(context, pathname)
            self.failUnlessEqual(x, resolved)
            self.failUnlessEqual(obnam.io.unsolve(context, x), pathname)

        self.failUnlessEqual(obnam.io.unsolve(context, "/pink"), "pink")


class IoBase(unittest.TestCase):

    def setUp(self):
        self.cachedir = "tmp.cachedir"
        self.rootdir = "tmp.rootdir"
        
        os.mkdir(self.cachedir)
        os.mkdir(self.rootdir)
        
        config_list = (
            ("backup", "cache-dir", self.cachedir),
            ("backup", "local-store", self.rootdir)
        )
    
        self.context = obnam.context.create()
    
        for section, item, value in config_list:
            if not self.context.config.has_section(section):
                self.context.config.add_section(section)
            self.context.config.set(section, item, value)

        self.context.cache = obnam.cache.init(self.context.config)
        self.context.be = obnam.backend.init(self.context.config, 
                                                self.context.cache)

    def tearDown(self):
        shutil.rmtree(self.cachedir)
        shutil.rmtree(self.rootdir)
        del self.cachedir
        del self.rootdir
        del self.context


class ObjectQueueFlushing(IoBase):

    def testEmptyQueue(self):
        obnam.io.flush_object_queue(self.context, self.context.oq, 
                                       self.context.map)
        list = obnam.backend.list(self.context.be)
        self.failUnlessEqual(list, [])

    def testFlushing(self):
        obnam.obj.object_queue_add(self.context.oq, "pink", "pretty")
        
        self.failUnlessEqual(obnam.backend.list(self.context.be), [])
        
        obnam.io.flush_object_queue(self.context, self.context.oq,
                                       self.context.map)

        list = obnam.backend.list(self.context.be)
        self.failUnlessEqual(len(list), 1)
        
        b1 = os.path.basename(obnam.mapping.get(self.context.map, "pink"))
        b2 = os.path.basename(list[0])
        self.failUnlessEqual(b1, b2)

    def testFlushAll(self):
        obnam.obj.object_queue_add(self.context.oq, "pink", "pretty")
        obnam.obj.object_queue_add(self.context.content_oq, "x", "y")
        obnam.io.flush_all_object_queues(self.context)
        self.failUnlessEqual(len(obnam.backend.list(self.context.be)), 2)
        self.failUnlessEqual(
          obnam.obj.object_queue_combined_size(self.context.oq), 0)
        self.failUnlessEqual(
          obnam.obj.object_queue_combined_size(self.context.content_oq), 0)


class GetObjectTests(IoBase):

    def upload_object(self, object_id, object):
        obnam.obj.object_queue_add(self.context.oq, object_id, object)
        obnam.io.flush_object_queue(self.context, self.context.oq,
                                       self.context.map)

    def testGetObject(self):
        id = "pink"
        component = obnam.cmp.create(42, "pretty")
        object = obnam.obj.create(id, 0)
        obnam.obj.add(object, component)
        object = obnam.obj.encode(object)
        self.upload_object(id, object)
        o = obnam.io.get_object(self.context, id)

        self.failUnlessEqual(obnam.obj.get_id(o), id)
        self.failUnlessEqual(obnam.obj.get_kind(o), 0)
        list = obnam.obj.get_components(o)
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(obnam.cmp.get_kind(list[0]), 42)
        self.failUnlessEqual(obnam.cmp.get_string_value(list[0]), 
                             "pretty")


class HostBlock(IoBase):

    def testFetchHostBlock(self):
        host_id = self.context.config.get("backup", "host-id")
        host = obnam.obj.host_block_encode(host_id, ["gen1", "gen2"],
                                                 ["map1", "map2"], 
                                                 ["contmap1", "contmap2"])
        be = obnam.backend.init(self.context.config, self.context.cache)
        
        obnam.io.upload_host_block(self.context, host)
        host2 = obnam.io.get_host_block(self.context)
        self.failUnlessEqual(host, host2)


class ObjectQueuingTests(unittest.TestCase):

    def find_block_files(self, config):
        files = []
        root = config.get("backup", "local-store")
        for dirpath, _, filenames in os.walk(root):
            files += [os.path.join(dirpath, x) for x in filenames]
        files.sort()
        return files

    def testEnqueue(self):
        context = obnam.context.create()
        object_id = "pink"
        object = "pretty"
        context.config.set("backup", "block-size", "%d" % 128)
        context.cache = obnam.cache.init(context.config)
        context.be = obnam.backend.init(context.config, context.cache)

        self.failUnlessEqual(self.find_block_files(context.config), [])
        
        obnam.io.enqueue_object(context, context.oq, context.map, 
                                   object_id, object)
        
        self.failUnlessEqual(self.find_block_files(context.config), [])
        self.failUnlessEqual(
            obnam.obj.object_queue_combined_size(context.oq),
            len(object))
        
        object_id2 = "pink2"
        object2 = "x" * 1024

        obnam.io.enqueue_object(context, context.oq, context.map, 
                                   object_id2, object2)
        
        self.failUnlessEqual(len(self.find_block_files(context.config)), 1)
        self.failUnlessEqual(
            obnam.obj.object_queue_combined_size(context.oq),
            len(object2))

        shutil.rmtree(context.config.get("backup", "cache-dir"))
        shutil.rmtree(context.config.get("backup", "local-store"))


class FileContentsTests(unittest.TestCase):

    def setUp(self):
        self.context = obnam.context.create()
        self.context.cache = obnam.cache.init(self.context.config)
        self.context.be = obnam.backend.init(self.context.config, 
                                                self.context.cache)

    def tearDown(self):
        for x in ["cache-dir", "local-store"]:
            if os.path.exists(self.context.config.get("backup", x)):
                shutil.rmtree(self.context.config.get("backup", x))

    def testEmptyFile(self):
        filename = "/dev/null"
        
        id = obnam.io.create_file_contents_object(self.context, filename)

        self.failIfEqual(id, None)
        self.failUnlessEqual(obnam.obj.object_queue_ids(self.context.oq), 
                             [id])
        self.failUnlessEqual(obnam.mapping.count(self.context.map), 0)
            # there's no mapping yet, because the queue is small enough
            # that there has been no need to flush it

    def testNonEmptyFile(self):
        block_size = 16
        self.context.config.set("backup", "block-size", "%d" % block_size)
        filename = "Makefile"
        
        id = obnam.io.create_file_contents_object(self.context, filename)

        self.failIfEqual(id, None)
        self.failUnlessEqual(obnam.obj.object_queue_ids(self.context.oq),
                                                           [id])

    def testRestore(self):
        block_size = 16
        self.context.config.set("backup", "block-size", "%d" % block_size)
        filename = "Makefile"
        
        id = obnam.io.create_file_contents_object(self.context, filename)
        obnam.io.flush_object_queue(self.context, self.context.oq,
                                       self.context.map)
        obnam.io.flush_object_queue(self.context, self.context.content_oq,
                                       self.context.contmap)
        
        (fd, name) = tempfile.mkstemp()
        obnam.io.get_file_contents(self.context, fd, id)
        os.close(fd)
        
        f = file(name, "r")
        data1 = f.read()
        f.close()
        os.remove(name)
        
        f = file(filename, "r")
        data2 = f.read()
        f.close()
        
        self.failUnlessEqual(data1, data2)


class MetaDataTests(unittest.TestCase):

    def testSet(self):
        fields = (
            (obnam.cmp.CMP_ST_MODE, 0100664),
            (obnam.cmp.CMP_ST_ATIME, 12765),
            (obnam.cmp.CMP_ST_MTIME, 42),
        )
        list = [obnam.cmp.create(kind, obnam.varint.encode(value))
                for kind, value in fields]
        inode = obnam.cmp.create(obnam.cmp.CMP_FILE, list)

        (fd, name) = tempfile.mkstemp()
        os.close(fd)
        
        os.chmod(name, 0)
        
        obnam.io.set_inode(name, inode)
        
        st = os.stat(name)
        
        self.failUnlessEqual(st.st_mode, fields[0][1])
        self.failUnlessEqual(st.st_atime, fields[1][1])
        self.failUnlessEqual(st.st_mtime, fields[2][1])


class ObjectCacheTests(unittest.TestCase):

    def setUp(self):
        self.object = obnam.obj.create("pink", 1)
        self.object2 = obnam.obj.create("pretty", 1)
        self.object3 = obnam.obj.create("beautiful", 1)

    def testCreate(self):
        context = obnam.context.create()
        oc = obnam.io.ObjectCache(context)
        self.failUnlessEqual(oc.size(), 0)
        self.failUnless(oc.MAX > 0)
        
    def testPut(self):
        context = obnam.context.create()
        oc = obnam.io.ObjectCache(context)
        self.failUnlessEqual(oc.get("pink"), None)
        oc.put(self.object)
        self.failUnlessEqual(oc.get("pink"), self.object)

    def testPutWithOverflow(self):
        context = obnam.context.create()
        oc = obnam.io.ObjectCache(context)
        oc.MAX = 1
        oc.put(self.object)
        self.failUnlessEqual(oc.size(), 1)
        self.failUnlessEqual(oc.get("pink"), self.object)
        oc.put(self.object2)
        self.failUnlessEqual(oc.size(), 1)
        self.failUnlessEqual(oc.get("pink"), None)
        self.failUnlessEqual(oc.get("pretty"), self.object2)

    def testPutWithOverflowPart2(self):
        context = obnam.context.create()
        oc = obnam.io.ObjectCache(context)
        oc.MAX = 2

        oc.put(self.object)
        oc.put(self.object2)
        self.failUnlessEqual(oc.size(), 2)
        self.failUnlessEqual(oc.get("pink"), self.object)
        self.failUnlessEqual(oc.get("pretty"), self.object2)

        oc.get("pink")
        oc.put(self.object3)
        self.failUnlessEqual(oc.size(), 2)
        self.failUnlessEqual(oc.get("pink"), self.object)
        self.failUnlessEqual(oc.get("pretty"), None)
        self.failUnlessEqual(oc.get("beautiful"), self.object3)


class ReachabilityTests(IoBase):

    def testNoDataNoMaps(self):
        host_id = self.context.config.get("backup", "host-id")
        host = obnam.obj.host_block_encode(host_id, [], [], [])
        obnam.io.upload_host_block(self.context, host)
        
        list = obnam.io.find_reachable_data_blocks(self.context, host)
        self.failUnlessEqual(list, [])
        
        list2 = obnam.io.find_map_blocks_in_use(self.context, host, list)
        self.failUnlessEqual(list2, [])

    def testNoDataExtraMaps(self):
        obnam.mapping.add(self.context.map, "pink", "pretty")
        map_block_id = "box"
        map_block = obnam.mapping.encode_new_to_block(self.context.map,
                                                         map_block_id)
        obnam.backend.upload(self.context.be, map_block_id, map_block)

        obnam.mapping.add(self.context.contmap, "black", "beautiful")
        contmap_block_id = "fiddly"
        contmap_block = obnam.mapping.encode_new_to_block(
                            self.context.contmap, contmap_block_id)
        obnam.backend.upload(self.context.be, contmap_block_id, 
                                contmap_block)

        host_id = self.context.config.get("backup", "host-id")
        host = obnam.obj.host_block_encode(host_id, [], [map_block_id], 
                                              [contmap_block_id])
        obnam.io.upload_host_block(self.context, host)
        
        list = obnam.io.find_map_blocks_in_use(self.context, host, [])
        self.failUnlessEqual(list, [])

    def testDataAndMap(self):
        o = obnam.obj.create("rouge", obnam.obj.OBJ_FILEPART)
        c = obnam.cmp.create(obnam.cmp.CMP_FILECHUNK, "moulin")
        obnam.obj.add(o, c)
        encoded_o = obnam.obj.encode(o)
        
        block_id = "pink"
        oq = obnam.obj.object_queue_create()
        obnam.obj.object_queue_add(oq, "rouge", encoded_o)
        block = obnam.obj.block_create_from_object_queue(block_id, oq)
        obnam.backend.upload(self.context.be, block_id, block)

        obnam.mapping.add(self.context.contmap, "rouge", block_id)
        map_block_id = "pretty"
        map_block = obnam.mapping.encode_new_to_block(self.context.contmap,
                                                         map_block_id)
        obnam.backend.upload(self.context.be, map_block_id, map_block)

        host_id = self.context.config.get("backup", "host-id")
        host = obnam.obj.host_block_encode(host_id, [], [], [map_block_id])
        obnam.io.upload_host_block(self.context, host)
        
        list = obnam.io.find_map_blocks_in_use(self.context, host, 
                                                  [block_id])
        self.failUnlessEqual(list, [map_block_id])


class GarbageCollectionTests(IoBase):

    def testFindUnreachableFiles(self):
        host_id = self.context.config.get("backup", "host-id")
        host = obnam.obj.host_block_encode(host_id, [], [], [])
        obnam.io.upload_host_block(self.context, host)

        block_id = obnam.backend.generate_block_id(self.context.be)
        obnam.backend.upload(self.context.be, block_id, "pink")

        files = obnam.backend.list(self.context.be)
        self.failUnlessEqual(files, [host_id, block_id])

        obnam.io.collect_garbage(self.context, host)
        files = obnam.backend.list(self.context.be)
        self.failUnlessEqual(files, [host_id])


class ObjectCacheRegressionTest(unittest.TestCase):

    # This test case is for a bug in obnam.io.ObjectCache: with the
    # right sequence of operations, the cache can end up in a state where
    # the MRU list is too long, but contains two instances of the same
    # object ID. When the list is shortened, the first instance of the
    # ID is removed, and the object is also removed from the dictionary.
    # If the list is still too long, it is shortened again, by removing
    # the last item in the list, but that no longer is in the dictionary,
    # resulting in the shortening not happening. Voila, an endless loop.
    #
    # As an example, if the object queue maximum size is 3, the following
    # sequence exhibits the problem:
    #
    #       put('a')        mru = ['a']
    #       put('b')        mru = ['b', 'a']
    #       put('c')        mru = ['c', 'b', 'a']
    #       put('a')        mru = ['a', 'c', 'b', 'a'], shortened into
    #                           ['c', 'b', 'a'], and now dict no longer
    #                           has 'a'
    #       put('d')        mru = ['d', 'c', 'b', 'a'], which needs to be
    #                           shortened by removing the last element, but
    #                           since 'a' is no longer in dict, the list
    #                           doesn't actually become shorter, and
    #                           the shortening loop becomes infinite
    #
    # (The fix to the bug is, of course, to forget the object to be 
    # inserted before inserting it, thus removing duplicates in the MRU
    # list.)

    def test(self):
        context = obnam.context.create()
        context.config.set("backup", "object-cache-size", "3")
        oc = obnam.io.ObjectCache(context)
        a = obnam.obj.create("a", 0)
        b = obnam.obj.create("b", 0)
        c = obnam.obj.create("c", 0)
        d = obnam.obj.create("d", 0)
        oc.put(a)
        oc.put(b)
        oc.put(c)
        oc.put(a)
        # If the bug is there, the next method call doesn't return.
        # Beware the operator.
        oc.put(b)


class LoadMapTests(IoBase):

    def test(self):
        map = obnam.mapping.create()
        obnam.mapping.add(map, "pink", "pretty")
        block_id = obnam.backend.generate_block_id(self.context.be)
        block = obnam.mapping.encode_new_to_block(map, block_id)
        obnam.backend.upload(self.context.be, block_id, block)
        
        obnam.io.load_maps(self.context, self.context.map, [block_id])
        self.failUnlessEqual(obnam.mapping.get(self.context.map, "pink"),
                             "pretty")
        self.failUnlessEqual(obnam.mapping.get(self.context.map, "black"),
                             None)