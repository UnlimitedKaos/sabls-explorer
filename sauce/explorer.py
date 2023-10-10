import re
import os
from pathlib import Path

class SablsUnarchiver:
    path_blocksize = 32 * 4
    
    def load_archive(archive: Path) -> bytearray:
        # Load file into ram
        with open(archive, "rb") as archive_file:
            archive_data = archive_file.read()
        
        return archive_data
    
    def __default_progress_callback(progress: float):
        if progress != float('inf'):
            print("\r{:0.2f}%".format(progress), end='')
        else:
            print("\rArchived Indexed")
    
    def find_flacs(archive: bytearray, progress_callback=__default_progress_callback) -> list[(int, str)]:
        # Search archive for flac files
        #   Looking for files via magic nums, if there are other filetypes in the archive
        #     Ill need to also search for those
        #     Also, im not tracking how big the flacs are, im just relying on the next file's magic num
        #       to be where this file ends. If there are other types of files in the archive, this is gonna fuck up
        
        flacs = [] # [ (offset, file path), (offset, file path), (offset, filepath), ... ]
        
        # find locations of file magic numbers (I think they're all FLACs)
        magic_nums = re.finditer(bytes("fLaC".encode("utf-8")), archive)
        for magic_num in magic_nums:
            flacs.append((magic_num.start(), None))
            if progress_callback:
                progress_callback(magic_num.start()/len(archive)*100)
        if progress_callback:
            progress_callback(float('inf'))
        
        # there appears to be file structure info at the end of the archive
        #   however, there doenst seem to be a preamble/magic number to indicate the start of filenames.
        #
        # it appears each path is 128 bytes long, (4 32byte words?)
        #   and they are in the order of the FLAC files. 
        # Also, if there is a filetype that I dont know about, ig this is just kinda fucked.
        #   Maybe I should search for other magic numbers?
        file_paths = archive[ -(len(flacs) * SablsUnarchiver.path_blocksize) : ]  # slice off last n-many blocks
        for i in range(len(flacs)): 
            flacs[i] = (flacs[i][0], file_paths[ (i * SablsUnarchiver.path_blocksize) : ((i + 1) * SablsUnarchiver.path_blocksize) ])
        
        return flacs
    
    def select_file(archive: bytearray, flacs: list[(int, str)], index: int) -> bytearray:
        if index+1 == len(flacs):
            file = archive[flacs[index][0]:-(len(flacs) * SablsUnarchiver.path_blocksize)]
        else:
            file = archive[flacs[index][0]:flacs[index+1][0]]
        return file
    
    def dump_archive(unarchive_path: Path, archive: bytearray, flacs: list[(int, str)]):
        # Unarchives the entire archive
        for i in range(len(flacs)):
            SablsUnarchiver.write_file(
                unarchive_path / SablsUnarchiver.to_filepath(flacs[i][1]),
                SablsUnarchiver.select_file(archive, flacs, i)
            )
    
    def dump_file(unarchive_path: Path, archive: bytearray, flacs: list[(int, str)], index: int):
        # Unarchives specific file
        SablsUnarchiver.write_file(
            unarchive_path / SablsUnarchiver.to_filepath(flacs[index][1]),
            SablsUnarchiver.select_file(archive, flacs, index)
        )
    
    def array_path_tree(input, silent=False):
        # If I was smart I would strip the flacs[] for just the 2nd value in each tuple, but Im not
        
        # creates a dict shaped like the file tree
        tree = {}
        untitled = 0
        for path in input:
            path = path[1].strip(b'\0').decode("utf-8")
            if path != "":
                layer = tree
                for level in path.split("\\"):
                    if not level in layer.keys():
                        layer.update({level: {}})
                    layer = layer[level]
            else:
                untitled += 1
                if not "No Name" in tree.keys():
                    tree.update({"No Name": {}})
                tree["No Name"].update({"file {:04d}".format(untitled): {}})
        
        # pretty-er dict print
        def print_tree(layer, indent=1):
            for key in layer.keys():
                #print("  " * indent + key)
                for i in reversed(range(indent)):
                    if i == 0:
                        print("+ ", end="")
                    else:
                        print("| ", end="")
                print(key)
                print_tree(layer[key], indent+1)
        
        if not silent:
            print_tree(tree)
        return tree
    
    def write_file(filepath: Path, contents: bytearray):
        # Prepares filepath and writes file
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as file:
            file.write(contents)
    
    def to_filepath(path: bytearray) -> Path:
        # Clean up unarchived data into a useful path
        file_name = path.strip(b'\0').replace(b'\\', b'/').decode("utf-8") + ".flac"
        if file_name == "":
            file_name = "not-named"
        return Path(file_name)

def cancer():
    def array_path_tree(input):
        tree = {}
        for path in input:
            path = path[1].strip(b'\0').decode("utf-8")
            layer = tree
            for level in path.split("\\"):
                if not level in layer.keys():
                    layer.update({level: {}})
                layer = layer[level]
        
        def print_tree(layer, indent=1):
            for key in layer.keys():
                print("    " * indent + key)
                print_tree(layer[key], indent+1)
        
        print_tree(tree)
    
    def write_file(filepath: str, contents: bytearray):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as file:
            file.write(contents)
    
    def to_filepath(path: bytearray) -> str:
        return unarchive_path / Path(path.strip(b'\0').replace(b'\\', b'/').decode("utf-8") + ".flac")
    
    archive_path = Path("./Game Files/all/zm_asylum.all.sabs")
    unarchive_path = Path("./unarchived")
    
    with open(archive_path, "rb") as audio_archive:
        # begin flac search
        audio_archive = audio_archive.read()  # load them naughty bytes into ram
        flacs = []  # [ [offset, file path], [offset, file path], [offset, file path] ... ]    
        
        # this is really fucking inefficient
        # for i in range(len(audio_archive)):  
        #     if audio_archive[ i : i+4 ] == bytes("fLaC", "utf-8"):  # search for fLaC magic number
        #         flacs.append([i, None, None])
        #         print("FLAC Offset: {:0.2f}%, hex: 0x{:02x}".format(i/len(audio_archive)*100, i))
        
        magic_nums = re.finditer(bytes("(fLaC)", "utf-8"), audio_archive)  # regex for fLaC magic number
        for magic_num in magic_nums:
            flacs.append([magic_num.start(), None])
            print("{:0.2f}%".format(magic_num.start()/len(audio_archive)*100))
            #print("FLAC Offset: {:0.2f}%, hex: 0x{:02x}".format(magic_num.start()/len(audio_archive)*100, magic_num.start()))
        print("finished indexing archive")
        
        if(len(flacs) == 0):
            print("Archive appears to be empty")
            exit(1)
        print(len(flacs))
        
        # there appears to be file structure info at the end of the archive
        #   however, there doenst seem to be a preamble/magic number to indicate the start of filenames.
        #
        # it appears each path is 128 bytes long, (4 32byte words?)
        #   and they are in the order of the FLAC files. 
        # Also, if there is a filetype that I dont know about, ig this is just kinda fucked.
        #   Maybe I should search for other magic numbers?
        path_blocksize = 32 * 4
        file_paths = audio_archive[ -(len(flacs) * path_blocksize) : ]  # slice off last n-many blocks
        for i in range(len(flacs)): 
            flacs[i][1] = file_paths[ (i * path_blocksize) : ((i + 1) * path_blocksize) ]
        
        if( id(audio_archive[-(len(flacs) * path_blocksize)]) == id(flacs[0][1][0]) ):
            print("Pointer party")
        else:
            print("Lol, sry ram")
        
        def dump_all():
            for i in range(len(flacs)):
                if i+2 > len(flacs):
                    file = audio_archive[flacs[i][0]:-(len(flacs) * path_blocksize)]
                else:
                    file = audio_archive[flacs[i][0]:flacs[i+1][0]]
                
                write_file(
                    to_filepath(flacs[i][1]),
                    file
                )
        
        
        
        array_path_tree(flacs)
        dump_all()


if __name__ == "__main__":
    archive_path = Path("./Game Files/all/zm_asylum.all.sabs")
    unarchive_path = Path("./experiments/unarchive")
    
    archive_data = SablsUnarchiver.load_archive(archive_path)
    flacs = SablsUnarchiver.find_flacs(archive_data)
    
    if len(flacs) == 0:
        print("Archive appears to be empty")
        exit(1)
    
    archive_tree = SablsUnarchiver.array_path_tree(flacs)
    SablsUnarchiver.dump_archive(archive_data, flacs)
    
    import json
    with open("./experiments/test_tree.json", "w") as file:
        file.write(json.dumps(archive_tree))

