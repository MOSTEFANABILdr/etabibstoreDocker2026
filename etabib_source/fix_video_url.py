from clinique.models import CliniqueVirtuelle

# Known working embeddable video (Me at the zoo)
SAFE_VIDEO_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

def fix_videos():
    cliniques = CliniqueVirtuelle.objects.all()
    count = 0
    for clinique in cliniques:
        if clinique.video:
            print(f"Updating video for {clinique.titre} (User: {clinique.user.username})")
            print(f"Old URL: {clinique.video}")
            clinique.video = SAFE_VIDEO_URL
            clinique.save()
            print(f"New URL: {clinique.video}")
            count += 1
    
    print(f"Updated {count} clinique videos.")

if __name__ == "__main__":
    fix_videos()
