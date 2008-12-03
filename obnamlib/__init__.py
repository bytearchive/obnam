# obnamlib/__init__.py
#
# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


from exception import BackupException as Exception
from component import Component
from object import Object
from object_factory import ObjectFactory
from store import Store
from vfs import VirtualFileSystem
from vfs_local import LocalFS

import varint

from kinds import Kinds
from component_kinds import ComponentKinds
from object_kinds import ObjectKinds

cmp_kinds = ComponentKinds()
cmp_kinds.add_all()
cmp_kinds.add_to_obnamlib()

obj_kinds = ObjectKinds()
obj_kinds.add_all()
obj_kinds.add_to_obnamlib()
