import hashlib
import os
import sys
from datetime import datetime


def dedup_files_by_size(directory: str) -> dict:
    files_info = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            size = os.path.getsize(path)
            if size not in files_info:
                files_info[size] = []
            files_info[size].append(path)
    return {x: files_info[x] for x in files_info if len(files_info[x]) > 1}


def get_chunk_md5(file_path: str, chunk_size=65536):
    with open(file_path, "rb") as fp:
        while True:
            chunk = fp.read(chunk_size)
            if not chunk:
                break
            yield hashlib.md5(chunk).hexdigest()


def dedup_file_list_by_md5(file_list: list) -> list[list]:
    dedup_files_list_tmp = [[(x, get_chunk_md5(x)) for x in file_list]]
    while True:
        try:
            done = True
            new_files_list = []
            for files in dedup_files_list_tmp:
                if len(files) > 1:
                    done = False
                    new_md5_files = {}
                    for file, md5_iter in files:
                        md5 = next(md5_iter)
                        if md5 not in new_md5_files:
                            new_md5_files[md5] = []
                        new_md5_files[md5].append((file, md5_iter))
                    new_files_list.extend([new_md5_files[x] for x in new_md5_files if len(new_md5_files[x]) > 1])
            dedup_files_list_tmp = new_files_list
            if done:
                break
        except StopIteration as e:
            break
    dedup_files_list = []
    for files in dedup_files_list_tmp:
        dedup_files_list.append([x[0] for x in files])
    return dedup_files_list


def dedup_files_in_directory(directory: str):
    files_by_size = dedup_files_by_size(directory)
    for size, files in files_by_size.items():
        for l in dedup_file_list_by_md5(files):
            if len(l) > 1:
                yield l


def get_file_info(file_path: str) -> tuple:
    return (os.path.getsize(file_path),
            datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    print(list(dedup_files_in_directory(sys.argv[1])))
