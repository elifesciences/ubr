elifeLibrary({
    stage 'Checkout', {
        checkout scm
    }

    stage 'Project tests', {
        elifeLocalTests "./project_tests.sh"
    }

    elifeMainlineOnly {
        stage 'Publishing to master', {
            elifeGitMoveToBranch commit, 'master'
        }
    }
})
