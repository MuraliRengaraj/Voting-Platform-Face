document.addEventListener('DOMContentLoaded', (event) => {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');
    const captureButton = document.getElementById('capture');
    const retakeButton = document.getElementById('retake');
    const faceImageInput = document.getElementById('face_image');
    const capturedImage = document.getElementById('capturedImage');

    let stream;

    // Access the webcam
    navigator.mediaDevices.getUserMedia({ video: true })
        .then((mediaStream) => {
            stream = mediaStream;
            video.srcObject = stream;
            video.play();
        })
        .catch((error) => {
            console.error('Error accessing webcam:', error);
        });

    // Capture the image
    captureButton.addEventListener('click', () => {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Convert image to base64 string
        const dataURL = canvas.toDataURL('image/jpeg');
        faceImageInput.value = dataURL;

        // Show the captured image
        capturedImage.src = dataURL;
        capturedImage.style.display = 'block';

        // Show retake button and hide capture button
        captureButton.style.display = 'none';
        retakeButton.style.display = 'block';

        // Optionally, stop the video stream
        if (stream) {
            const tracks = stream.getTracks();
            tracks.forEach(track => track.stop());
        }
    });

    // Retake the image
    retakeButton.addEventListener('click', () => {
        // Show capture button and hide retake button
        captureButton.style.display = 'block';
        retakeButton.style.display = 'none';

        // Clear the captured image
        capturedImage.src = '';
        capturedImage.style.display = 'none';

        // Restart the video stream
        navigator.mediaDevices.getUserMedia({ video: true })
            .then((mediaStream) => {
                stream = mediaStream;
                video.srcObject = stream;
                video.play();
            })
            .catch((error) => {
                console.error('Error accessing webcam:', error);
            });
    });
});
