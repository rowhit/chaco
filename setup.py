from setuptools import setup, Extension, find_packages
from numpy import get_include


contour = Extension(
    'enthought.chaco2.contour.contour',
    sources=['enthought/chaco2/contour/cntr.c'],
    include_dirs=[get_include()],
    define_macros=[('NUMPY', None)]
)


# Function to convert simple ETS project names and versions to a requirements
# spec that works for both development builds and stable builds.  Allows
# a caller to specify a max version, which is intended to work along with
# Enthought's standard versioning scheme -- see the following write up:
#    https://svn.enthought.com/enthought/wiki/EnthoughtVersionNumbers
def etsdep(p, min, max=None, literal=False):
    require = '%s >=%s.dev' % (p, min)
    if max is not None:
        if literal is False:
            require = '%s, <%s.a' % (require, max)
        else:
            require = '%s, <%s' % (require, max)
    return require


# Declare our ETS project dependencies.
ENABLE2 = etsdep('enthought.enable2', '2.0.0b1')
ETSCONFIG = etsdep('enthought.etsconfig', '2.0.0b1')
KIVA = etsdep('enthought.kiva', '2.0.0b1')
TRAITS = etsdep('enthought.traits', '2.0.0b1')


setup(
    author = 'Enthought, Inc',
    author_email = 'info@enthought.com',
    dependency_links = [
        'http://code.enthought.com/enstaller/eggs/source',
        'http://code.enthought.com/enstaller/eggs/source/unstable',
        ],
    description = 'Chaco plotting toolkit',
    extras_require = {
        # All non-ets dependencies should be in this extra to ensure users can
        # decide whether to require them or not.
        'nonets': [
            'numpy >=1.0.2',
            ],
        },
    ext_modules = [contour],
    include_package_data = True,
    install_requires = [
        ENABLE2,
        ETSCONFIG,
        KIVA,
        TRAITS,
        ],
    license = 'BSD',
    name = 'enthought.chaco2',
    namespace_packages = [
        "enthought",
        ],
    packages = find_packages(
        exclude=['docs', 'examples', 'examples.zoomed_plot'],
        ),
    tests_require = [
        'nose >= 0.9',
        ],
    test_suite = 'nose.collector',
    url = 'http://code.enthought.com/chaco',
    version='3.0.0a1',
    zip_safe = False,
    )