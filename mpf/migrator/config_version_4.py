
section_deprecations = '''
timing:
plugins:

# holdpatter
# pwm_on
# pwm_off
# player_controlled_eject_tag


# display element shape names to lowercase?

'''

section_replacements = ''

section_transformations = ''

def custom_migration(file_contents):
    print('doing custom migration')
    return file_contents

def get_warnings(file_contents):
    print('getting warnings')
    return file_contents