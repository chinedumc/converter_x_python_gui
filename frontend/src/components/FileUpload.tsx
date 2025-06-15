import React from "react";
import { validateFile, convertFile } from "@/lib/api";
import { useToast } from "@/components/ui/toast"; // <-- use the hook

function FileUpload() {
	const { toast } = useToast();
	const [file, setFile] = React.useState<File | null>(null);

	const handleValidate = async () => {
		if (!file) return;
		try {
			const result = await validateFile(file);
			toast({ title: "Validation", description: result.message });
		} catch (e: any) {
			toast({ title: "Error", description: e.message, variant: "destructive" });
		}
	};

	const handleConvert = async () => {
		if (!file) return;
		try {
			const result = await convertFile(file);
			toast({ title: "Success", description: "File converted!" });
			window.location.href = result.downloadUrl;
		} catch (e: any) {
			toast({ title: "Error", description: e.message, variant: "destructive" });
		}
	};

	// ...render file input and buttons
}

export default FileUpload;
