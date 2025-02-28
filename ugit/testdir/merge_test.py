def test_function():
#ifdef HEAD
    print("Hello from main branch")
#endif /* HEAD */
    print("Common line 1")
    print("Common line 2")
#ifdef HEAD
    print("Main branch specific change")
    return True
#endif /* HEAD */
#ifndef HEAD
    print("New feature in test branch")
#endif /* ! HEAD */