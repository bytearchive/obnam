"""Unit tests for wibbrlib."""


import os
import unittest


from wibbrlib.component import *
from wibbrlib.object import *
from wibbrlib.varint import *
import wibbrlib


class ComponentTypeNameTests(unittest.TestCase):

    def test(self):
        c = component_type_name
        self.failUnlessEqual(c(-12765), "CMP_UNKNOWN")
        self.failUnlessEqual(c(CMP_OBJID), "CMP_OBJID")
        self.failUnlessEqual(c(CMP_OBJTYPE), "CMP_OBJTYPE")
        self.failUnlessEqual(c(CMP_BLKID), "CMP_BLKID")
        self.failUnlessEqual(c(CMP_FILEDATA), "CMP_FILEDATA")
        self.failUnlessEqual(c(CMP_OBJPART), "CMP_OBJPART")
        self.failUnlessEqual(c(CMP_OBJMAP), "CMP_OBJMAP")
        self.failUnlessEqual(c(CMP_ST_MODE), "CMP_ST_MODE")
        self.failUnlessEqual(c(CMP_ST_INO), "CMP_ST_INO")
        self.failUnlessEqual(c(CMP_ST_DEV), "CMP_ST_DEV")
        self.failUnlessEqual(c(CMP_ST_NLINK), "CMP_ST_NLINK")
        self.failUnlessEqual(c(CMP_ST_UID), "CMP_ST_UID")
        self.failUnlessEqual(c(CMP_ST_GID), "CMP_ST_GID")
        self.failUnlessEqual(c(CMP_ST_SIZE), "CMP_ST_SIZE")
        self.failUnlessEqual(c(CMP_ST_ATIME), "CMP_ST_ATIME")
        self.failUnlessEqual(c(CMP_ST_MTIME), "CMP_ST_MTIME")
        self.failUnlessEqual(c(CMP_ST_CTIME), "CMP_ST_CTIME")
        self.failUnlessEqual(c(CMP_ST_BLOCKS), "CMP_ST_BLOCKS")
        self.failUnlessEqual(c(CMP_ST_BLKSIZE), "CMP_ST_BLKSIZE")
        self.failUnlessEqual(c(CMP_ST_RDEV), "CMP_ST_RDEV")
        self.failUnlessEqual(c(CMP_CONTREF), "CMP_CONTREF")
        self.failUnlessEqual(c(CMP_NAMEIPAIR), "CMP_NAMEIPAIR")
        self.failUnlessEqual(c(CMP_INODEREF), "CMP_INODEREF")
        self.failUnlessEqual(c(CMP_FILENAME), "CMP_FILENAME")
        self.failUnlessEqual(c(CMP_SIGDATA), "CMP_SIGDATA")
        self.failUnlessEqual(c(CMP_SIGREF), "CMP_SIGREF")
        self.failUnlessEqual(c(CMP_GENREF), "CMP_GENREF")
        self.failUnlessEqual(c(CMP_GENLIST), "CMP_GENLIST")
        self.failUnlessEqual(c(CMP_OBJREF), "CMP_OBJREF")
        self.failUnlessEqual(c(CMP_BLOCKREF), "CMP_BLOCKREF")


class ObjectTypeNameTests(unittest.TestCase):

    def test(self):
        self.failUnlessEqual(object_type_name(-12765), "OBJ_UNKNOWN")
        self.failUnlessEqual(object_type_name(OBJ_FILECONT), "OBJ_FILECONT")
        self.failUnlessEqual(object_type_name(OBJ_INODE), "OBJ_INODE")
        self.failUnlessEqual(object_type_name(OBJ_GEN), "OBJ_GEN")
        self.failUnlessEqual(object_type_name(OBJ_SIG), "OBJ_SIG")
        self.failUnlessEqual(object_type_name(OBJ_HOST), "OBJ_HOST")


class VarintEncoding(unittest.TestCase):

    def testZero(self):
        self.failUnlessEqual(varint_encode(0), "\0")

    def testNegative(self):
        self.failUnlessRaises(AssertionError, varint_encode, -1)

    def testSmallPositives(self):
        self.failUnlessEqual(varint_encode(1), "\1")
        self.failUnlessEqual(varint_encode(127), "\177")

    def test128(self):
        self.failUnlessEqual(varint_encode(128), "\x81\0")

    def testBigPositive(self):
        self.failUnlessEqual(varint_encode(0xff00),
                             "\203\376\0")


class VarintDecodeTests(unittest.TestCase):

    def testZero(self):
        self.failUnlessEqual(varint_decode("\0", 0), (0, 1))

    def testSmall(self):
        self.failUnlessEqual(varint_decode("\1", 0), (1, 1))
        self.failUnlessEqual(varint_decode("\177", 0), (127, 1))

    def test128(self):
        self.failUnlessEqual(varint_decode("\x81\0", 0), (128, 2))

    def testBigPositive(self):
        self.failUnlessEqual(varint_decode("\203\376\0", 0), 
                             (0xff00, 3))


class VarintEncodeDecodeTests(unittest.TestCase):

    def test(self):
        numbers = (0, 1, 127, 128, 0xff00)
        for i in numbers:
            str = varint_encode(i)
            (i2, pos) = varint_decode(str, 0)
            self.failUnlessEqual(i, i2)
            self.failUnlessEqual(pos, len(str))


class ComponentEncodingDecodingTests(unittest.TestCase):

    def doit(self, type, data):
        str = component_encode(type, data)
        (type2, data2, pos) = component_decode(str, 0)
        self.failUnlessEqual(type, type2)
        self.failUnlessEqual(data, data2)
        self.failUnlessEqual(pos, len(str))

    def testEmpty(self):
        self.doit(1, "")

    def testNonempty(self):
        self.doit(2, "hello, world\0this is fun")


class ComponentDecodeAllTests(unittest.TestCase):

    def testDecodeAll(self):
        c1 = component_encode(1, "pink")
        c2 = component_encode(2, "pretty")
        c = c1 + c2
        list = component_decode_all(c, 0)
        self.failUnlessEqual(list, [(1, "pink"), (2, "pretty")])


class ObjectEncodingTests(unittest.TestCase):

    def testEmptyObject(self):
        self.failUnlessEqual(object_encode("uuid", 33, []),
                             "\4\1uuid\1\2\41")

    def testNonEmptyObject(self):
        self.failUnlessEqual(object_encode("uuid", 33, ["\1\77x"]),
                             "\4\1uuid\1\2\41\1\77x")


class ObjectEncodingDecodingTests(unittest.TestCase):

    def test(self):
        component1 = component_encode(0xdeadbeef, "hello")
        component2 = component_encode(0xcafebabe, "world")
        object = object_encode("uuid", 0xdada, [component1, component2])
        self.failIfEqual(object, None)
        self.failIfEqual(object, "")
        
        components = object_decode(object, 0)
        self.failUnlessEqual(len(components), 4) # id, type, cmpnt1, cmpnt2
        
        self.failUnlessEqual(components[0], (CMP_OBJID, "uuid"))
        self.failUnlessEqual(components[1], (CMP_OBJTYPE, 0xdada))
        self.failUnlessEqual(components[2], (0xdeadbeef, "hello"))
        self.failUnlessEqual(components[3], (0xcafebabe, "world"))


class ObjectQueueTests(unittest.TestCase):

    def testCreate(self):
        self.failUnlessEqual(object_queue_create(), [])

    def testAdd(self):
        oq = object_queue_create()
        object_queue_add(oq, "xx", "abc")
        self.failUnlessEqual(oq, [("xx", "abc")])

    def testSize(self):
        oq = object_queue_create()
        self.failUnlessEqual(object_queue_combined_size(oq), 0)
        object_queue_add(oq, "xx", "abc")
        self.failUnlessEqual(object_queue_combined_size(oq), 3)
        object_queue_add(oq, "yy", "abc")
        self.failUnlessEqual(object_queue_combined_size(oq), 6)


class BlockCreateTests(unittest.TestCase):

    def testEmptyObjectQueue(self):
        oq = object_queue_create()
        block = block_create_from_object_queue("blkid", oq)
        self.failUnlessEqual(block, "\5\3blkid")
        self.failUnlessEqual(object_queue_ids(oq), [])

    def testObjectQueue(self):
        oq = object_queue_create()
        object_queue_add(oq, "xx", "foo")
        block = block_create_from_object_queue("blkid", oq)
        self.failUnlessEqual(block, "\5\3blkid\3\5foo")
        self.failUnlessEqual(object_queue_ids(oq), ["xx"])


class InodeTests(unittest.TestCase):

    def testEncodeDecode(self):
        stats1 = normalize_stat_result(os.stat("wibbrlibTests.py"))
        id1 = "xyzzy"
        sigref1 = "maze"
        contref1 = "plugh"
        inode = inode_object_encode(id1, stats1, sigref1, contref1)
        (id2, stats2, sigref2, contref2) = inode_object_decode(inode)
        self.failUnlessEqual(id1, id2)
        self.failUnlessEqual(stats1, stats2)
        self.failUnlessEqual(sigref1, sigref2)
        self.failUnlessEqual(contref1, contref2)


class GenerationTests(unittest.TestCase):

    def testEncodeDecode(self):
        id1 = "xyzzy"
        pairs1 = [("inode1", "cont1"), ("inode2", "cont2")]
        gen = generation_object_encode(id1, pairs1)
        (id2, pairs2) = generation_object_decode(gen)
        self.failUnlessEqual(id1, id2)
        self.failUnlessEqual(pairs1, pairs2)
        

class RsyncTests(unittest.TestCase):

    def testSignature(self):
        sig = wibbrlib.rsync.compute_signature("/dev/null")
        os.system("rdiff signature /dev/null devnull.sig.temp")
        f = file("devnull.sig.temp")
        data = f.read()
        f.close()
        self.failUnlessEqual(sig, data)
        os.remove("devnull.sig.temp")

    def testEmptyDelta(self):
        sig = wibbrlib.rsync.compute_signature("/dev/null")
        delta = wibbrlib.rsync.compute_delta(sig, "/dev/null")
        # The hex string below is what rdiff outputs. I've no idea what
        # the format is, and the empty delta is expressed differently
        # in different situations. Eventually we'll move away from rdiff,
        # and then this should become clearer. --liw, 2006-09-24
        self.failUnlessEqual(delta, "rs\x026\x00")


class NormalizedInodeTests(unittest.TestCase):

    def testNormalization(self):
        st1 = os.stat("Makefile")
        st2 = os.stat(".")
        st3 = os.stat("..")
        nst1 = normalize_stat_result(st1)
        nst2 = normalize_stat_result(st2)
        nst3 = normalize_stat_result(st3)
        self.failUnlessEqual(nst1, normalize_stat_result(st1))
        self.failUnlessEqual(nst2, normalize_stat_result(st2))
        self.failUnlessEqual(nst3, normalize_stat_result(st3))
        self.failIfEqual(nst1, nst2)
        self.failIfEqual(nst2, nst3)
        self.failIfEqual(nst3, nst1)


class ObjectTests(unittest.TestCase):

    def testId(self):
        id = wibbrlib.object.object_id_new()
        self.failIfEqual(id, None)
        self.failUnlessEqual(type(id), type(""))

    def testCreateSignatureObject(self):
        id = "pink"
        sig = wibbrlib.rsync.compute_signature("Makefile")
        object = signature_object_encode(id, sig)
        self.failUnlessEqual(object, "".join(["\4\1pink", # obj id
                                              "\1\2\4",   # obj type
                                              chr(len(sig)) + "\30" + sig,
                                              ]))


class ObjectMappingTests(unittest.TestCase):

    def testEmpty(self):
        m = wibbrlib.mapping.create()
        self.failUnlessEqual(wibbrlib.mapping.count(m), 0)

    def testGetNonexisting(self):
        m = wibbrlib.mapping.create()
        blkids = wibbrlib.mapping.get(m, "pink")
        self.failUnlessEqual(blkids, None)

    def testAddOneMapping(self):
        m = wibbrlib.mapping.create()
        wibbrlib.mapping.add(m, "pink", "pretty")
        self.failUnlessEqual(wibbrlib.mapping.count(m), 1)
        
        blkids = wibbrlib.mapping.get(m, "pink")
        self.failUnlessEqual(blkids, ["pretty"])

    def testAddTwoMappings(self):
        m = wibbrlib.mapping.create()
        wibbrlib.mapping.add(m, "pink", "pretty")
        wibbrlib.mapping.add(m, "pink", "beautiful")
        self.failUnlessEqual(wibbrlib.mapping.count(m), 1)
        
        blkids = wibbrlib.mapping.get(m, "pink")
        self.failUnlessEqual(blkids, ["pretty", "beautiful"])

    def testGetNewMappings(self):
        m = wibbrlib.mapping.create()
        self.failUnlessEqual(wibbrlib.mapping.get_new(m), [])
        wibbrlib.mapping.add(m, "pink", "pretty")
        self.failUnlessEqual(wibbrlib.mapping.get_new(m), ["pink"])
        wibbrlib.mapping.reset_new(m)
        self.failUnlessEqual(wibbrlib.mapping.get_new(m), [])
        wibbrlib.mapping.add(m, "black", "beautiful")
        self.failUnlessEqual(wibbrlib.mapping.get_new(m), ["black"])

    def testMappingEncodings(self):
        # Set up a mapping
        m = wibbrlib.mapping.create()
        
        # It's empty; make sure encoding new ones returns an empty list
        list = wibbrlib.mapping.encode_new(m)
        self.failUnlessEqual(list, [])

        # Add a mapping
        wibbrlib.mapping.add(m, "pink", "pretty")

        # Encode the new mapping, make sure that goes well
        list = wibbrlib.mapping.encode_new(m)
        self.failUnlessEqual(len(list), 1)
        
        # Make sure the encoding is correct
        list2 = wibbrlib.component.component_decode_all(list[0], 0)
        self.failUnlessEqual(len(list2), 1)
        self.failUnlessEqual(list2[0][0], wibbrlib.component.CMP_OBJMAP)
        
        list3 = wibbrlib.component.component_decode_all(list2[0][1], 0)
        self.failUnlessEqual(len(list3), 2)
        self.failUnlessEqual(list3[0], 
                             (wibbrlib.component.CMP_OBJREF, "pink"))
        self.failUnlessEqual(list3[1], 
                             (wibbrlib.component.CMP_BLOCKREF, "pretty"))

        # Now try decoding with the official function
        block = wibbrlib.mapping.encode_new_to_block(m, "black")
        m2 = wibbrlib.mapping.create()
        wibbrlib.mapping.decode_block(m2, block)
        self.failUnlessEqual(wibbrlib.mapping.count(m2), 1)
        self.failUnlessEqual(wibbrlib.mapping.get(m2, "pink"), ["pretty"])


class HostBlockTests(unittest.TestCase):

    def testEncodeDecode(self):
        host_id = "pink"
        gen_ids = ["pretty", "beautiful"]
        host = wibbrlib.object.host_block_encode(host_id, gen_ids)
        (host_id2, gen_ids2) = wibbrlib.object.host_block_decode(host)
        self.failUnlessEqual(host_id, host_id2)
        self.failUnlessEqual(gen_ids, gen_ids2)


if __name__ == "__main__":
    unittest.main()
