elifeLibrary({
    def commit
    stage 'Checkout', {
        checkout scm
        commit = elifeGitRevision()
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
