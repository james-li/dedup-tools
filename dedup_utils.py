import asyncio
import hashlib
import logging
import os
import sys
import traceback
from datetime import datetime

import aiofiles as aiofiles


class dedup_process_helper_interface(object):
    async def info(self, message):
        pass


class dedup_process_helper(dedup_process_helper_interface):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def info(self, message):
        self.logger.info(message)


class dedup_utils(object):
    def __init__(self, directory: str, helper: dedup_process_helper_interface = None):
        self.directory = directory
        self.helper = helper

    async def set_info(self, message):
        if self.helper:
            await self.helper.info(message)

    def dedup_files_by_size(self) -> dict:
        files_info = {}
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                path = os.path.join(root, file)
                size = os.path.getsize(path)
                if size not in files_info:
                    files_info[size] = []
                files_info[size].append(path)
        return {x: files_info[x] for x in files_info if len(files_info[x]) > 1}

    async def get_file_md5_by_chunk(self, file_path: str, chunk_size=65536):
        md5_hash = hashlib.md5()
        async with aiofiles.open(file_path, "rb") as fp:
            while True:
                chunk = await fp.read(chunk_size)
                if not chunk:
                    break
                # await self.set_info(file_path)
                md5_hash.update(chunk)
                yield md5_hash.hexdigest()

    async def get_chunk_md5(self, file_path, md5_iter, dedup_files_by_chunk_md5: dict, lock):
        md5 = await next(md5_iter)
        async with lock:
            if md5 not in dedup_files_by_chunk_md5:
                dedup_files_by_chunk_md5[md5] = []
            dedup_files_by_chunk_md5[md5].append((file_path, md5_iter))

    async def dedup_file_list_by_md5(self, file_list: list) -> list[list]:
        dedup_files_list_tmp = [[(x, self.get_file_md5_by_chunk(x)) for x in file_list]]
        lock = asyncio.Lock()
        while True:
            try:
                done = True
                new_files_list = []
                for files in dedup_files_list_tmp:
                    if len(files) > 1:
                        done = False
                        new_md5_files = {}
                        # tasks = []
                        for file_path, md5_iter in files:
                            md5 = await md5_iter.__anext__()
                            async with lock:
                                if md5 not in new_md5_files:
                                    new_md5_files[md5] = []
                                new_md5_files[md5].append((file_path, md5_iter))
                        new_files_list.extend([new_md5_files[x] for x in new_md5_files if len(new_md5_files[x]) > 1])
                dedup_files_list_tmp = new_files_list
                if done:
                    break
            except StopAsyncIteration as e:
                break
            except BaseException as e:
                traceback.print_exc()
                break

        dedup_files_list = []
        for files in dedup_files_list_tmp:
            dedup_files_list.append([x[0] for x in files])
        return dedup_files_list

    async def dedup_files_in_directory(self):
        files_by_size = self.dedup_files_by_size()
        for size, files in files_by_size.items():
            file_list = await self.dedup_file_list_by_md5(files)
            for l in file_list:
                if len(l) > 1:
                    yield l

    @staticmethod
    def get_file_info(file_path: str) -> tuple:
        return (
            os.path.getsize(file_path),
            datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%Y-%m-%d %H:%M:%S"),
        )


async def main(directory: str):
    print("Start dedup files in %s" % directory)
    dutils = dedup_utils(directory, dedup_process_helper())
    async for files in dutils.dedup_files_in_directory():
        print(files)
    # files = dutils.dedup_files_by_size()
    # file_path = files[[key for key in files.keys() if key > 32768][0]][0]
    # md5_iter = dutils.get_file_md5_by_chunk(file_path, 32768)
    # while True:
    #     try:
    #         md5 = await md5_iter.__anext__()
    #         print(md5)
    #     except BaseException as e:
    #         traceback.print_exc()
    #         break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
    asyncio.run(main(sys.argv[1]))
