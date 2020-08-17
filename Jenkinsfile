pipeline {
    agent any

    stages {
        stage('build daemon') {
            steps {
                dir('daemon') {
                    sh 'make build'
                }
            }
        }
        stage('test daemon') {
            steps {
                dir('daemon') {
                    sh 'make test'
                }
            }
        }
        stage('lint daemon') {
            steps {
                dir('daemon') {
                    sh 'make lint'
                }
            }
        }
        stage('push daemon') {
            when {
                branch 'master'
            }
            steps {
                dir('daemon') {
                    sh 'make push'
                }
            }
        }
    }
}
