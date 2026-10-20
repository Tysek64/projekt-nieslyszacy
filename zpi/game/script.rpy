define videos_path = '/var/ftp/share'
define video_paths = []
define video_index = 0
define frame_index = 0
define require_redraw = True
define x_pos = 0
define y_pos = 0
define is_labeling = False
define label_start = None
define label_full = None
define db_files = {}
define total_videos = 0
define processed_videos = 0

define k = Character('くーにゃん', color="#c8ffc8")
define p = Character('パソコンくん', color='#00ffff')

init python:
    from pathlib import Path
    import math
    import os
    import random
    import re
    import subprocess
    import json

    def change_frame():
        global frame_index
        global require_redraw
        frame_index = random.randint(0, 60*2)
        require_redraw = True

    def change_video():
        global video_index
        global require_redraw
        global label_full
        global db_files
        global processed_videos

        if label_full is not None:
            db_files[str(video_paths[video_index])] = (
                int(min(800, max(0, label_full[0]))),
                int(min(450, max(0, label_full[1]))),
                int(min(800, max(0, label_full[2]))),
                int(min(450, max(0, label_full[3])))
            )
            save_video_to_db()
            video_paths.remove(video_paths[video_index])
            processed_videos = len(db_files.keys())

            label_full = None

            if len(video_paths) == 0:
                renpy.hide_screen('test')
                return

            video_index = random.randint(0, len(video_paths) - 1)
            change_frame()

            require_redraw = True

    def change_video_empty():
        global video_index
        global require_redraw
        global label_full
        global db_files
        global processed_videos

        if label_full is None:
            db_files[str(video_paths[video_index])] = [-1, -1, -1, -1]
            save_video_to_db()
            video_paths.remove(video_paths[video_index])
            processed_videos = len(db_files.keys())

            if len(video_paths) == 0:
                renpy.hide_screen('test')
                return

            video_index = random.randint(0, len(video_paths) - 1)
            change_frame()

            require_redraw = True

    def cancel_this_mode():
        renpy.hide_screen('test')

    def start_label():
        global is_labeling
        is_labeling = True

    def stop_label():
        global is_labeling
        is_labeling = False

    def get_video_paths():
        global video_paths
        global total_videos

        batch_folders = [folder for folder in os.listdir(videos_path) if re.search(r'batch\d+', folder) is not None]

        video_paths = []

        total_videos = 0
        for folder in batch_folders:
            for file in os.listdir(videos_path / Path(folder)):
                total_videos += 1
                if folder != 'processed' and folder != 'on_server':
                    if str(videos_path / Path(folder) / Path(file)) not in db_files.keys():
                        video_paths.append(videos_path / Path(folder) / Path(file))

    def get_videos_in_db():
        global db_files
        global processed_videos

        try:
            with open(videos_path / Path('labels.json')) as file:
                json.load(file)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            out_file = open(videos_path / Path('labels.json'), mode='w')
            out_file.write('{}')
            out_file.close()

        with open(videos_path / Path('labels.json')) as file:
            db_files = json.load(file)
            processed_videos = len(db_files.keys())

    def save_video_to_db():
        global db_files
        with open(videos_path / Path('labels.json'), mode='w') as file:
            json.dump(db_files, file)

    change_frame()
    get_videos_in_db()
    get_video_paths()

    class VideoFrame(renpy.Displayable):
        def __init__(self, **kwargs):
            super(VideoFrame, self).__init__(**kwargs)

            self.width = 0
            self.height = 0

            self.video_frame = None

            self.crosshair = renpy.displayable("crosshair.png")

        def read_frames(self):
            global frame_index
            global video_index
            global x_pos
            global require_redraw

            x_pos += 1
            x_pos %= 100

            self.path = video_paths[video_index]

            args = ["ffmpeg", "-ss", str(frame_index), "-i", self.path, "-vf", "scale=800:450", "-vframes", "1", "-f", "image2pipe", "-pix_fmt", "rgba", "-vcodec", "rawvideo", "-"]

            pipe = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )

            require_redraw = False

            return renpy.load_rgba(pipe.stdout, (800, 450))

        def render(self, width, height, st, at):
            global x_pos
            global y_pos
            global require_redraw
            global label_start
            global label_full
            global is_labeling

            render = renpy.Render(800, 450)

            if require_redraw or self.video_frame is None:
                self.video_frame = self.read_frames()

            render.blit(self.video_frame, (0, 0))


            width = 0
            height = 0
            left = 0
            top = 0
            if is_labeling and label_start is not None:
                width = abs(x_pos - label_start[0]) / 800
                height = abs(y_pos - label_start[1]) / 450

                left = min(x_pos, label_start[0])
                top = min(y_pos, label_start[1])

            if not is_labeling and label_full is not None:
                width = abs(label_full[2] - label_full[0]) / 800
                height = abs(label_full[3] - label_full[1]) / 450

                left = min(label_full[2], label_full[0])
                top = min(label_full[3], label_full[1])


            label_rect = Transform(Solid('#ff0000'), crop=(0, 0, width, height), alpha=0.5)
            label_render = renpy.render(label_rect, 800, 450, st, at)
            render.blit(label_render, (left, top))


            cropped_crosshair = Transform(self.crosshair, crop=(0, 0, 1 - x_pos / 1600, 1 - y_pos / 900))
            crosshair_render = renpy.render(cropped_crosshair, 1600, 900, st, at)

            render.blit(crosshair_render, (x_pos - 800, y_pos - 450))


            return render

        def event(self, ev, x, y, st):
            global y_pos
            global x_pos
            global label_start
            global label_full
            global is_labeling

            y_pos = y
            x_pos = x
            renpy.redraw(self, 0)

            if is_labeling and label_start is None:
                label_full = None
                label_start = (x, y)

            if not is_labeling:
                if label_start is not None:
                    label_full = (label_start[0], label_start[1], x, y)
                label_start = None

            return self.crosshair.event(ev, x, y, st)

        
        def visit(self):
            return [ self.crosshair ]

screen test:
    hbox:
        add VideoFrame():
            xalign 0.25
            yalign 0.5
        frame:
            hbox:
                vbox:
                    text "別のフレーム"
                    text "別の動画"
                    text "別の動画（ラベルなし）"
                    text "キャンセル"
                    text "進化："
                vbox:
                    text "'s'"
                    text "'d'"
                    text "'f'"
                    text "'g'"
                    text "[processed_videos]/[total_videos]"

    key 's' action Function(change_frame)
    key 'd' action Function(change_video)
    key 'f' action Function(change_video_empty)
    key 'g' action Function(cancel_this_mode)

    key "mousedown_1" action Function(start_label)
    key "mouseup_1" action Function(stop_label)

image chara1:
    "sozai_22_b.png"
    zoom 0.5
    
image chara_paso:
    "sozai_53_b.png"
    zoom 0.5

label start:
    scene bg outside

    show chara1 at center

    with dissolve

    k "おにーさん！新しいデータをダウンロードしたいの？"
    
label sentaku_start:
    k "さて、どこに行くか？"
    
menu:
    "デフォルト設定を確認する":
        jump check_settings

    "リンクから動画をダウンロードする":
        jump download_from_link
        
    "動画にラベルをつける":
        jump label_videos
        
    "ラベルによってファイルを切る":
        jump crop_videos
        
    "部活のサーバへ送信する":
        jump send_to_server
        
label check_settings:
    k "何を確認したいの？"
        
menu:
    "動画のダウンロード先：[videos_path]":
        jump change_video_folder
        
    "全部良さそう":
        jump sentaku_start
        
label change_video_folder:
    python:
        videos_path = renpy.input("新しい動画のダウンロード先", default=videos_path)
        
    jump check_settings
        
label download_from_link:
    k "よーし！リンクはどこにあるの？"
    
    show chara1:
        xalign 0.25
        yalign 1.0
    
    show chara_paso:
        xalign 0.75
        yalign 1.0
    
    k "お〜パソコンくんだ！"
    p "コンニチハ。パソコンクン　ト　モウシマス。"
    
    python:
        import subprocess
        import time
        import multiprocessing
        import os
        import re
        from pathlib import Path

        if 'processed' not in os.listdir(videos_path):
            os.mkdir(videos_path / Path('processed'))

        if 'on_server' not in os.listdir(videos_path):
            os.mkdir(videos_path / Path('on_server'))

        batch_folders = [-1] + [int(re.search(r'\d+', folder)[0]) for folder in os.listdir(videos_path) if re.search(r'batch\d+', folder) is not None]

        os.mkdir(videos_path / Path(f'batch{max(batch_folders) + 1}'))
        
        file_location = renpy.input('リンク　ハ　ドコ　デス　カ？')
        
        def run_subprocess(link):
            subprocess.run(['yt-dlp', link, '-o', videos_path / Path(f'batch{max(batch_folders) + 1}') / Path('%(id)s.%(ext)s')])
        
        with open(file_location) as file:
            for _, link in zip(range(10), file):
                process = multiprocessing.Process(target=run_subprocess, args=(link,))
                process.start()
                num = 0
                while process.is_alive():
                    p('[link]　ヲ　ダウンロード　チュウ　デス' + ('.' * (num + 1)) + '{nw=1}')
                    num += 1
                    num %= 3
                process.join()
                
        p('ダウンロード　ガ　カンリョウ　シマシタ。')
    
    k "ありがとね、パソコンくん♡"
    p "ドウモ。"

    jump loop
    
label label_videos:
    k "ラベルテックに任せて！"
    
    python:
        get_videos_in_db()
        get_video_paths()

    if len(video_paths) > 0:
        show screen test
        k '好きにして♪'
    else:
        k 'お疲れ様！'

    jump loop
    
label crop_videos:
    k "ちょっと待ってね〜"
    
    show chara1:
        xalign 0.25
        yalign 1.0
    
    show chara_paso:
        xalign 0.75
        yalign 1.0

    k "おー！またパソコンくん"

    p "コンニチハ。パソコンクン　ト　モウシマス。"

    python:
        import subprocess
        import threading

        def run_subprocess_2(link, return_value):
            ret_val = subprocess.run(['ffmpeg', '-i', file[0], '-vf', f'crop={width}:{height}:{left}:{top}', '-c:v', 'libx264', '-crf', '17', '-c:a', 'copy', link], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
            print(ret_val)
            return_value[0] = ret_val

        files = {}
        return_value = {0: None}
        try:
            with open(videos_path / Path('labels.json')) as file:
                files = json.load(file)
        except:
            p('ラベル　ガ　アリマセン、マタ　ハ　ファイル　ガ　コワレテ　イマス。ゴメンナサイ。')

        for i, file in enumerate(files.items(), start=1):
            filename = file[0][file[0].rfind('/')+1:file[0].rfind('.')] + '_PROCESSED'
            dir_name = videos_path / Path('processed')

            try:
                file_test = open(dir_name / Path(filename + '.mp4'))
                file_test.close()
                p(file[0] + '　ㇵ　スデ　二　コンバート　サレテ　イマス。{nw=1}')
                continue
            except FileNotFoundError:
                pass

            try:
                file_test = open(videos_path / Path('on_server') / Path(filename + '.mp4'))
                file_test.close()
                p(file[0] + '　ㇵ　スデ　二　コンバート　サレテ　イマス。{nw=1}')
                continue
            except FileNotFoundError:
                pass

            try:
                resolution = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'default=nw=1:nk=1', file[0]], stdout=subprocess.PIPE).stdout.decode('utf-8')
                width, height = resolution.split('\n')[:2]
                video_width = int(width)
                video_height = int(height)

                width_ratio = video_width / 800
                height_ratio = video_height / 450

                rect = file[1]

                left = int(min(rect[0], rect[2]) * width_ratio)
                top = int(min(rect[1], rect[3]) * height_ratio)

                width = int(abs(rect[0] - rect[2]) * width_ratio)
                height = int(abs(rect[1] - rect[3]) * height_ratio)

                if rect[0] == -1 or rect[1] == -1 or rect[2] == -1 or rect[3] == -1:
                    p(file[0] + '二　ㇵ　ブリンカー　ガ　アリマセン。{nw=1}')
                else:
                    process = threading.Thread(target=run_subprocess_2, args=(str(dir_name / Path(filename + '.mp4')), return_value))
                    process.start()
                    num = 0
                    while process.is_alive():
                        p(file[0] + '　ヲ　コンバート　チュウ　デス' + ('.' * (num + 1)) + '{nw=1}')
                        num += 1
                        num %= 3
                    process.join()

                    print(return_value)
                    assert(return_value[0] == 0)
            except Exception as e:
                p(file[0] + '　ㇵ　サクジョ　サレテ　イル　カ　モ　シレマセン。{nw=1}')
                
        p('コンバート　ガ　カンリョウ　シマシタ。')
    
    k "ありがとね、パソコンくん♡"
    p "ドウモ。"

    jump loop
    
label send_to_server:
    k "パソコンくん、たすけて！"
    
    show chara1:
        xalign 0.25
        yalign 1.0
    
    show chara_paso:
        xalign 0.75
        yalign 1.0

    k "おー！野生のパソコンくんが現れた〜"

    p "コンニチハ。パソコンクン　ト　モウシマス。"

    python:
        import pexpect
        import os
        from pathlib import Path
        import threading

        hostname = renpy.input('ホスト　メイ　ヲ　ニュウリョク　シテ　クダサイ：')
        username = renpy.input('ユーザー　メイ　ヲ　ニュウリョク　シテ　クダサイ：')
        password = renpy.input('ソノ　ユーザー　ノ　パスワード　ヲ　ニュウリョク　シテ　クダサイ：', mask='♡')
        remote_path = renpy.input('リモート　パス　ヲ　ニュウリョク　シテ　クダサイ：')

        filename_queue = []

        def run_copy():
            child = pexpect.spawn(f'scp -r {videos_path / Path('processed')} {username}@{hostname}:{remote_path}', timeout=30)
            child.expect(['[pP]assword: '])
            child.sendline(password)
            seen_filenames = []
            try:
                while len(seen_filenames) < len(os.listdir(videos_path / Path('processed'))):
                    child.expect(r'.*\.mp4')
                    raw_filename = child.after.decode('utf-8')
                    raw_filename = raw_filename[:raw_filename.find('.mp4') + 4]
                    raw_filename = raw_filename.split()
                    filename = raw_filename[-1]
                    if filename not in seen_filenames:
                        seen_filenames.append(filename)
                        filename_queue.append(filename)

                child.expect(pexpect.EOF)
                child.close()
            except pexpect.exceptions.EOF:
                child.close()

        num = 0
        process = threading.Thread(target=run_copy)
        process.start()
        current_filename = ''
        while process.is_alive() or len(filename_queue) > 0:
            if len(filename_queue) > 0:
                current_filename = filename_queue.pop()
            p(current_filename + '　ヲ　コピー　チュウ　デス' + ('.' * (num + 1)) + '{nw=1}')
            num += 1
            num %= 3
        process.join()

        p('コピー　ガ　カンリョウ　シマシタ。')

        for file in os.listdir(videos_path / Path('processed')):
            os.rename(str(videos_path / Path('processed') / file), str(videos_path / Path('on_server') / file))
    
    k "ありがとね、パソコンくん♡"
    p "ドウモ。"

    jump loop

label loop:
    show chara1 at center
    hide chara_paso
    
    k "さてさて、他のどっかに行こー"
    
menu:
    "もちろん！":
        jump sentaku_start
        
    "今度…":
        jump end

label end:
    return

