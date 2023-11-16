def update_progress_bar(completed, total):
    bar_length = 20
    progress = completed / total
    block = int(round(bar_length * progress))
    text = "\rProgress: [{0}] {1:.0f}% Completed".format(
        "#" * block + "-" * (bar_length - block), progress * 100)
    print(text, end='')
