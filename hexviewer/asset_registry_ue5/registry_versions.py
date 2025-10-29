from enum import IntEnum, auto

class RegistryVersions(IntEnum):
	PRE_VERSIONING = 0,									# From before file versioning was implemented
	HARD_SOFT_DEPENDENCIES = auto()						# The first version of the runtime asset registry to include file versioning.
	ADD_ASSET_REGISTRY_STATE = auto()					# Added FAssetRegistryState and support for piecemeal serialization
	CHANGED_ASSET_DATA = auto()							# AssetData serialization format changed, versions before this are not readable
	REMOVED_MD5_HASH = auto()							# Removed MD5 hash from package data
	ADDED_HARD_MANAGE = auto()					    	# Added hard/soft manage references
	ADDED_COOKED_MD5_HASH = auto()						# Added MD5 hash of cooked package to package data
	ADDED_DEPENDENCY_FLAGS = auto()						# Added UE::AssetRegistry::EDependencyProperty to each dependency
	FIXED_TAGS = auto()									# Major tag format change that replaces USE_COMPACT_ASSET_REGISTRY:
														# * Target tag INI settings cooked into tag data
														# * Instead of FString values are stored directly as one of:
														#		- Narrow / wide string
														#		- [Numberless] FName
														#		- [Numberless] export path
														#		- Localized string
														# * All value types are deduplicated
														# * All key-value maps are cooked into a single contiguous range
														# * Switched from FName table to seek-free and more optimized FName batch loading
														# * Removed global tag storage, a tag map reference-counts one store per asset registry
														# * All configs can mix fixed and loose tag maps
	WORKSPACE_DOMAIN = auto()					    	# Added Version information to AssetPackageData
	PACKAGE_IMPORTED_CLASSES = auto()					# Added ImportedClasses to AssetPackageData
	PACKAGE_FILE_SUMMARY_VERSION_CHANGE = auto()	    # A new version number of UE5 was added to FPackageFileSummary
	OBJECT_RESOURCE_OPTIONAL_VERSION_CHANGE = auto() 	# Change to linker export/import resource serialization
	ADDED_CHUNK_HASHES = auto()							# Added FIoHash for each FIoChunkId in the package to the AssetPackageData.
	CLASS_PATHS = auto()						    	# Classes are serialized as path names rather than short object names, e.g. /Script/Engine.StaticMesh
	REMOVE_ASSET_PATH_FNAMES = auto()					# Asset bundles are serialized as FTopLevelAssetPath instead of FSoftObjectPath, deprecated FAssetData::ObjectPath
	ADDED_HEADER = auto()						    	# Added header with bFilterEditorOnlyData flag
	ASSET_PACKAGE_DATA_HAS_EXTENSION = auto()			# Added Extension to AssetPackageData.

	# -----<new versions can be added above this line>-------------------------------------------------
	VERSION_PLUS_ONE = auto()
	LATEST_VERSION = VERSION_PLUS_ONE - 1